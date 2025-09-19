import { useState, useCallback } from 'react';

interface ImageAnalysisResult {
  findings: string[];
  severity: string;
  recommendations: string[];
  clinical_coding?: {
    snomed_codes: Array<{
      code: string;
      display: string;
      system: string;
    }>;
  };
}

interface UseImageCaptureReturn {
  isAnalyzing: boolean;
  error: string | null;
  result: ImageAnalysisResult | null;
  captureFromCamera: () => Promise<void>;
  uploadFile: (file: File) => Promise<void>;
  clearResult: () => void;
}

export const useImageCapture = (): UseImageCaptureReturn => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImageAnalysisResult | null>(null);

  const analyzeImage = useCallback(async (file: File) => {
    setIsAnalyzing(true);
    setError(null);

    try {
      const token = localStorage.getItem('digiclinic_token');
      if (!token) {
        throw new Error('Authentication token not found');
      }

      const formData = new FormData();
      formData.append('file', file);
      formData.append('analysis_type', 'comprehensive');

      const response = await fetch('/api/medical/vision/analyze', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to analyze image');
      }

      const analysisResult = await response.json();
      setResult(analysisResult);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to analyze image';
      setError(errorMessage);
      console.error('Image analysis error:', err);
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  const captureFromCamera = useCallback(async () => {
    try {
      setError(null);
      
      // Request camera access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'environment' } // Prefer back camera for medical photos
      });

      // Create video element to capture frame
      const video = document.createElement('video');
      video.srcObject = stream;
      video.autoplay = true;
      video.muted = true;

      // Wait for video to load
      await new Promise((resolve) => {
        video.onloadedmetadata = resolve;
      });

      // Create canvas to capture frame
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      
      if (!ctx) {
        throw new Error('Failed to get canvas context');
      }

      // Capture frame
      ctx.drawImage(video, 0, 0);
      
      // Stop camera stream
      stream.getTracks().forEach(track => track.stop());

      // Convert to blob and analyze
      canvas.toBlob(async (blob) => {
        if (blob) {
          const file = new File([blob], 'camera-capture.jpg', { type: 'image/jpeg' });
          await analyzeImage(file);
        }
      }, 'image/jpeg', 0.9);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Camera access failed';
      setError(errorMessage);
      console.error('Camera capture error:', err);
    }
  }, [analyzeImage]);

  const uploadFile = useCallback(async (file: File) => {
    if (!file.type.startsWith('image/')) {
      setError('Please select a valid image file');
      return;
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      setError('Image file must be less than 10MB');
      return;
    }

    await analyzeImage(file);
  }, [analyzeImage]);

  const clearResult = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    isAnalyzing,
    error,
    result,
    captureFromCamera,
    uploadFile,
    clearResult,
  };
};