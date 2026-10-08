"use client";
import React from "react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle, AlertTriangle, FileText, BrainCircuit, Search, Database } from 'lucide-react';

// Types
type StatusPhase = "upload" | "upload_complete" | "parsing" | "classifying" | "saving" | "completed" | "error";

interface RealtimeProgressProps {
  progress: number;
  message: string;
  phase: StatusPhase;
  isError: boolean;
}

const phaseConfig = {
  upload: { icon: FileText, label: "Uploading" },
  upload_complete: { icon: CheckCircle, label: "Upload Complete" },
  parsing: { icon: BrainCircuit, label: "Parsing Resume" },
  classifying: { icon: Search, label: "Classifying Domain" },
  saving: { icon: Database, label: "Saving Analysis" },
  completed: { icon: CheckCircle, label: "Completed" },
  error: { icon: AlertTriangle, label: "Error" },
};

const RealtimeProgress: React.FC<RealtimeProgressProps> = ({
  progress,
  message,
  phase,
  isError,
}) => {
  const currentPhase = phaseConfig[phase] || phaseConfig.upload;

  return (
    <div className="w-full max-w-md rounded-2xl bg-gray-800/50 backdrop-blur-lg p-8 shadow-2xl border border-gray-700/50">
      <div className="flex flex-col items-center gap-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          {isError ? (
            <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-destructive" />
            </div>
          ) : progress < 100 ? (
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center animate-pulse">
               <Loader2 className="w-6 h-6 text-primary animate-spin" />
            </div>
          ) : (
             <div className="w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-green-500" />
            </div>
          )}
          <div>
            <h3 className="text-xl font-bold text-white">
              {isError ? "An Error Occurred" : "Analyzing Your Resume"}
            </h3>
            <p className="text-sm text-gray-400">Please wait, this may take a moment.</p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full space-y-3">
          <Progress value={progress} className={`h-3 ${isError ? 'bg-destructive' : ''}`} />
          <div className="flex justify-between items-center">
             <div className="flex items-center gap-2">
                <currentPhase.icon className={`w-4 h-4 ${isError ? 'text-destructive' : 'text-primary'}`} />
                <span className={`text-sm font-medium ${isError ? 'text-destructive' : 'text-gray-300'}`}>{currentPhase.label}</span>
            </div>
            <span className="text-sm font-semibold text-white">{progress.toFixed(0)}%</span>
          </div>
        </div>
        
        {/* Status Message */}
        <div className="w-full text-center p-3 bg-gray-900/50 rounded-lg">
            <p className="text-sm text-gray-300 italic">{message}</p>
        </div>
      </div>
    </div>
  );
};

export default RealtimeProgress;
