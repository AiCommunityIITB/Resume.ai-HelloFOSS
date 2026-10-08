"use client";

import React, { createContext, useState, ReactNode, useContext } from 'react';

interface ResumeContextType {
  file: File | null;
  setFile: (file: File | null) => void;
  imageUrls: string[];
  setImageUrls: (urls: string[]) => void;
  isGeneratingImages: boolean;
  setIsGeneratingImages: (generating: boolean) => void;
}

const ResumeContext = createContext<ResumeContextType | undefined>(undefined);

export const ResumeProvider = ({ children }: { children: ReactNode }) => {
  const [file, setFile] = useState<File | null>(null);
  const [imageUrls, setImageUrls] = useState<string[]>([]);
  const [isGeneratingImages, setIsGeneratingImages] = useState(false);

  return (
    <ResumeContext.Provider value={{ 
      file, 
      setFile, 
      imageUrls, 
      setImageUrls,
      isGeneratingImages,
      setIsGeneratingImages
    }}>
      {children}
    </ResumeContext.Provider>
  );
};

export const useResume = () => {
  const context = useContext(ResumeContext);
  if (context === undefined) {
    throw new Error('useResume must be used within a ResumeProvider');
  }
  return context;
};
