"use client";

import React, {
  useState,
  useCallback,
  type FC,
  type DragEvent,
  type ChangeEvent,
} from "react";
import {
  UploadCloud,
  FileText,
  X,
  Sparkles,
  ArrowRight,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Loader2,
  Upload,
} from "lucide-react";
import { useResume } from "@/context/ResumeContext";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import RealtimeProgress from "./RealtimeProgress";

// Types
type StatusPhase = "idle" | "upload" | "upload_complete" | "parsing" | "classifying" | "saving" | "completed" | "error";

interface ClassificationData {
  overall_classification: string;
  confidence: number;
}

// Constants
const JOB_ROLES = [
  "Analytics",
  "Consult", 
  "Design",
  "Finance",
  "IT-Software",
  "AI Developer",
  "Quantitative Finance",
  "Strategy",
] as const;

const ACCEPTED_FILE_TYPES = {
  "application/pdf": ".pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
  "image/png": ".png",
  "image/jpeg": ".jpg,.jpeg",
} as const;

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

// Utility functions
const formatBytes = (bytes: number, decimals = 2): string => {
  if (!bytes) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
};

const getFileIcon = (fileType: string) => {
  if (fileType === "application/pdf") return "📄";
  if (fileType.includes("word")) return "📝";
  if (fileType.includes("image")) return "🖼️";
  return "📄";
};

const UploadPage: FC = () => {
  // State management
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Real-time progress state
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisMessage, setAnalysisMessage] = useState("");
  const [analysisPhase, setAnalysisPhase] = useState<StatusPhase>("idle");
  const [isProcessing, setIsProcessing] = useState(false);

  // Classification modal state
  const [showClassificationModal, setShowClassificationModal] = useState(false);
  const [classificationData, setClassificationData] = useState<{
    classified: string;
    confidence: number;
    resumeId: number;
  } | null>(null);
  const [selectedDomain, setSelectedDomain] = useState<string>("");
  const [isUpdatingDomain, setIsUpdatingDomain] = useState(false);

  const router = useRouter();
  const { setFile: setResumeFile } = useResume();

  // File validation
  const validateFile = useCallback((file: File): string | null => {
    const validTypes = Object.keys(ACCEPTED_FILE_TYPES);
    
    if (!validTypes.includes(file.type)) {
      return `Unsupported file type. Please upload: ${Object.values(ACCEPTED_FILE_TYPES).join(", ")}`;
    }
    
    if (file.size > MAX_FILE_SIZE) {
      return `File size too large. Maximum size is ${formatBytes(MAX_FILE_SIZE)}.`;
    }
    
    if (file.size === 0) {
      return "File appears to be empty. Please select a valid file.";
    }
    
    return null;
  }, []);

  // File selection handler
  const handleFileSelect = useCallback((selectedFile: File | undefined) => {
    if (!selectedFile) return;
    
    const validationError = validateFile(selectedFile);
    if (validationError) {
      setError(validationError);
      toast.error(validationError);
      return;
    }
    
    setError(null);
    setFile(selectedFile);
    setResumeFile(selectedFile);
    toast.success("File selected successfully!");
  }, [validateFile, setResumeFile]);

  // Drag and drop handlers
  const handleDragEnter = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
  }, []);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
    
    const droppedFile = e.dataTransfer.files?.[0];
    handleFileSelect(droppedFile);
  }, [handleFileSelect]);

  const handleFileChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    handleFileSelect(selectedFile);
    e.target.value = "";
  }, [handleFileSelect]);

  // Upload and analyze resume
  const handleAnalyze = useCallback(async (fileToUpload: File) => {
    setIsProcessing(true);
    setAnalysisPhase("upload");
    setAnalysisProgress(0);
    setAnalysisMessage("Preparing to upload...");
    setError(null);

    const formData = new FormData();
    formData.append("file", fileToUpload);

    api.uploadWithSSE(
      "/api/v1/projects/upload-document",
      formData,
      (progress) => {
        // This is the onUploadProgress callback
        if (analysisPhase === 'upload') {
            setAnalysisProgress(progress);
            setAnalysisMessage(`Uploading file... ${progress}%`);
        }
      },
      (data) => {
        // This is the onMessage callback for SSE
        if (data.status === 'processing') {
          setAnalysisProgress(data.progress);
          setAnalysisMessage(data.message);
          setAnalysisPhase(data.phase);
        } else if (data.status === 'complete') {
          setAnalysisProgress(100);
          setAnalysisMessage(data.message);
          setAnalysisPhase("completed");
          setIsProcessing(false);

          const { resume_id, classified_domain } = data.result;
          const classification = classified_domain.overall_classification || "";
          const confidence = (classified_domain.confidence || 0) * 100;

          setClassificationData({
            classified: classification,
            confidence,
            resumeId: resume_id,
          });
          setSelectedDomain(classification);
          setShowClassificationModal(true);
          toast.success("Resume analyzed successfully!");
        } else if (data.status === 'error') {
            setError(data.message);
            setAnalysisPhase("error");
            setIsProcessing(false);
            toast.error(data.message);
        }
      },
      (error) => {
        // This is the onError callback
        console.error("Upload error:", error);
        setError(error.message || "Failed to upload and analyze resume");
        setAnalysisPhase("error");
        setIsProcessing(false);
        toast.error(error.message || "An unexpected error occurred.");
      }
    );
  }, [analysisPhase]);

  // Form submission
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file) {
      const errorMsg = "Please select a resume file first.";
      setError(errorMsg);
      toast.error(errorMsg);
      return;
    }

    await handleAnalyze(file);
  }, [file, handleAnalyze]);

  // Analyze resume with selected domain
  const handleFinalAnalysis = useCallback(async () => {
    if (!classificationData) return;

    try {
      setIsUpdatingDomain(true);

      if (selectedDomain !== classificationData.classified) {
        await api.put(
          `/api/v1/projects/resume/${classificationData.resumeId}`,
          { classified_domain: selectedDomain }
        );
      }

      toast.success("Redirecting to analysis...");
      router.push(`/analyze/${classificationData.resumeId}`);
      
    } catch (error: any) {
      console.error("Failed to update domain:", error);
      const errorMessage = error.response?.data?.message || "Failed to update domain";
      toast.error(errorMessage);
    } finally {
      setIsUpdatingDomain(false);
    }
  }, [classificationData, selectedDomain, router]);

  // Remove selected file
  const handleRemoveFile = useCallback(() => {
    setFile(null);
    setResumeFile(null);
    setError(null);
    setAnalysisPhase("idle");
    setAnalysisProgress(0);
  }, [setResumeFile]);

  // Retry upload
  const handleRetry = useCallback(() => {
    if (file) {
      handleAnalyze(file);
    }
  }, [file, handleAnalyze]);

  const acceptedFileTypes = Object.keys(ACCEPTED_FILE_TYPES).join(",");

  return (
    <main className="flex flex-col min-h-screen bg-gray-900">
      {/* Header */}
      <header className="flex flex-col items-center justify-center py-14 lg:py-24 text-center gap-4">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-tight bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
          Smart feedback for your{" "}
          <span className="whitespace-nowrap">dream job</span>
        </h1>
        <p className="max-w-2xl text-lg sm:text-xl text-muted-foreground">
          Upload your resume for an ATS score and personalized improvement tips.
        </p>
      </header>

      {/* Main Content */}
      <section className="flex-1 grid place-items-center px-4 sm:px-10 pb-24">
        {/* Processing Overlay */}
        {isProcessing && (
          <div className="fixed inset-0 z-40 grid place-items-center bg-background/80 backdrop-blur-sm">
            <RealtimeProgress 
              progress={analysisProgress}
              message={analysisMessage}
              phase={analysisPhase}
              isError={analysisPhase === 'error'}
            />
          </div>
        )}

        {/* Upload Form */}
        <form onSubmit={handleSubmit} className="w-full max-w-3xl space-y-8">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-muted-foreground">
              Upload Your Resume
            </label>
            
            {file ? (
              <div className="flex items-center justify-between gap-4 p-4 rounded-lg border border-border bg-muted/10 hover:bg-muted/20 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="text-2xl">{getFileIcon(file.type)}</div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate" title={file.name}>
                      {file.name}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{formatBytes(file.size)}</span>
                      <span>•</span>
                      <span>{file.type.split('/')[1].toUpperCase()}</span>
                    </div>
                  </div>
                </div>
                
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleRemoveFile}
                  className="text-muted-foreground hover:text-destructive"
                  disabled={isProcessing}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <div
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                className={`
                  border-2 border-dashed rounded-lg h-64 sm:h-72 
                  flex flex-col items-center justify-center gap-4 
                  cursor-pointer transition-all duration-200
                  ${dragging 
                    ? "border-primary bg-primary/5 scale-105" 
                    : "border-border hover:border-primary/50 hover:bg-muted/5"
                  }
                `}
              >
                <div className="text-center space-y-4">
                  <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                    <UploadCloud className="w-6 h-6 text-primary" />
                  </div>
                  
                  <div>
                    <p className="text-foreground font-medium">
                      <label
                        htmlFor="file-upload"
                        className="text-primary cursor-pointer hover:underline focus:outline-none focus:underline"
                      >
                        Click to upload
                      </label>{" "}
                      or drag and drop
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">
                      PDF, DOCX, PNG or JPG (max. {formatBytes(MAX_FILE_SIZE)})
                    </p>
                  </div>
                </div>
                
                <input
                  id="file-upload"
                  type="file"
                  className="sr-only"
                  onChange={handleFileChange}
                  accept={acceptedFileTypes}
                  disabled={isProcessing}
                />
              </div>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>{error}</span>
                {analysisPhase === "error" && file && (
                  <Button variant="outline" size="sm" onClick={handleRetry}>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry
                  </Button>
                )}
              </AlertDescription>
            </Alert>
          )}

          {/* Success Message */}
          {analysisPhase === "completed" && !error && (
            <Alert className="border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200">
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>
                Resume uploaded and analyzed successfully! Choose your domain classification below.
              </AlertDescription>
            </Alert>
          )}

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={!file || isProcessing}
            className="w-full py-6 text-lg font-semibold"
            size="lg"
          >
            {isProcessing ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                {analysisMessage || "Processing..."}
              </>
            ) : (
              <>
                <Upload className="mr-2 h-5 w-5" />
                Analyze My Resume
              </>
            )}
          </Button>
        </form>
      </section>

      {/* Classification Modal */}
      <Dialog open={showClassificationModal} onOpenChange={setShowClassificationModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-gradient-to-br from-primary to-accent rounded-xl flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <DialogTitle>AI Domain Classification</DialogTitle>
                <DialogDescription>
                  Our AI has analyzed your resume
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {classificationData && (
            <div className="space-y-6">
              {/* Classification Results */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Detected Domain:</span>
                  <Badge variant="secondary" className="font-medium">
                    {classificationData.classified}
                  </Badge>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Confidence:</span>
                    <span className="text-sm font-medium text-green-600">
                      {classificationData.confidence.toFixed(1)}%
                    </span>
                  </div>
                  <Progress 
                    value={classificationData.confidence} 
                    className="h-2"
                  />
                </div>
              </div>

              {/* Domain Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Confirm or change domain:
                </label>
                <Select value={selectedDomain} onValueChange={setSelectedDomain}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select domain" />
                  </SelectTrigger>
                  <SelectContent>
                    {JOB_ROLES.map((role) => (
                      <SelectItem key={role} value={role}>
                        <div className="flex items-center gap-2">
                          <span>{role}</span>
                          {role === classificationData.classified && (
                            <Badge variant="outline" className="text-xs">
                              AI Pick
                            </Badge>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setShowClassificationModal(false)}
                  className="flex-1"
                  disabled={isUpdatingDomain}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleFinalAnalysis}
                  className="flex-1"
                  disabled={isUpdatingDomain || !selectedDomain}
                >
                  {isUpdatingDomain ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <ArrowRight className="mr-2 h-4 w-4" />
                      Analyze Resume
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </main>
  );
};

export default UploadPage;
