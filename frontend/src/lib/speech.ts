// Voice Tutoring Helpers: Web Speech API Integration

export interface SpeechController {
  startListening: (onResult: (text: string) => void, onError?: (err: any) => void) => void;
  stopListening: () => void;
  speak: (text: string, onEnd?: () => void) => void;
  stopSpeaking: () => void;
  isSupported: boolean;
}

export function createSpeechController(): SpeechController {
  if (typeof window === 'undefined') {
    return {
      startListening: () => {},
      stopListening: () => {},
      speak: () => {},
      stopSpeaking: () => {},
      isSupported: false,
    };
  }

  const SpeechRecognition =
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

  let recognitionInstance: any = null;

  const isSupported = !!SpeechRecognition && 'speechSynthesis' in window;

  const startListening = (onResult: (text: string) => void, onError?: (err: any) => void) => {
    if (!SpeechRecognition) {
      if (onError) onError(new Error('Speech recognition is not supported in this browser.'));
      return;
    }

    try {
      if (recognitionInstance) {
        recognitionInstance.stop();
      }
      recognitionInstance = new SpeechRecognition();
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = false;
      recognitionInstance.lang = 'en-US';

      recognitionInstance.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        onResult(transcript);
      };

      recognitionInstance.onerror = (event: any) => {
        if (onError) onError(event.error);
      };

      recognitionInstance.start();
    } catch (err) {
      if (onError) onError(err);
    }
  };

  const stopListening = () => {
    if (recognitionInstance) {
      try {
        recognitionInstance.stop();
      } catch (_) {}
    }
  };

  const speak = (text: string, onEnd?: () => void) => {
    if (!('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      // Clean up markdown syntax for voice reading
      const cleanText = text
        .replace(/[*_~`#$]/g, '')
        .replace(/\[.*?\]/g, '')
        .replace(/\(.*?\)/g, '')
        .trim();

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = 0.95; // Slightly slower, clear cadence for student comprehension
      utterance.pitch = 1.05; // Warm, friendly tone
      if (onEnd) {
        utterance.onend = onEnd;
      }
      window.speechSynthesis.speak(utterance);
    } catch (_) {}
  };

  const stopSpeaking = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  };

  return {
    startListening,
    stopListening,
    speak,
    stopSpeaking,
    isSupported,
  };
}
