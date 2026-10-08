"use client";
import React, {
  useState,
  useCallback,
  useRef,
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
  Cloud,
  Brain,
  Database,
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

// Types
interface ClassificationData {
  overall_classification: string;
  confidence: number;
}

interface UploadResponse {
  success: boolean;
  data: {
    resume_id: number;
    classified_domain: ClassificationData;
  };
  message?: string;
}

type UploadStatus = 
  | "idle" 
  | "uploading" 
  | "upload_complete" 
  | "parsing" 
  | "classifying" 
  | "saving" 
  | "completed" 
  | "error";

interface ProcessingStep {
  name: string;
  icon: React.ReactNode;
  description: string;
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

const PROCESSING_STEPS: Record<UploadStatus, ProcessingStep> = {
  idle: { name: "Ready", icon: <Upload className="w-4 h-4" />, description: "Ready to upload" },
  uploading: { name: "Uploading", icon: <Cloud className="w-4 h-4" />, description: "Uploading file to server" },
  upload_complete: { name: "Upload Complete", icon: <CheckCircle className="w-4 h-4" />, description: "File uploaded successfully" },
  parsing: { name: "Parsing", icon: <FileText className="w-4 h-4" />, description: "Extracting text and structure" },
  classifying: { name: "Classifying", icon: <Brain className="w-4 h-4" />, description: "Analyzing domain expertise" },
  saving: { name: "Saving", icon: <Database className="w-4 h-4" />, description: "Saving to database" },
  completed: { name: "Complete", icon: <CheckCircle className="w-4 h-4" />, description: "Analysis completed successfully" },
  error: { name: "Error", icon: <AlertCircle className="w-4 h-4" />, description: "Processing failed" },
};

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
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<string>("");

  // Classification modal state
  const [showClassificationModal, setShowClassificationModal] = useState(false);
  const [classificationData, setClassificationData] = useState<{
    classified: string;
    confidence: number;
    resumeId: number;
  } | null>(null);
  const [selectedDomain, setSelectedDomain] = useState<string>("");
  const [isUpdatingDomain, setIsUpdatingDomain] = useState(false);

  // Fake progress refs and state
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const hasBackendResponseRef = useRef<boolean>(false);

  const router = useRouter();
  const { setFile: setResumeFile } = useResume();

  // Enhanced fake progress functions
  const startFakeProgress = () => {
    // Clear any existing interval
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }

    progressIntervalRef.current = setInterval(() => {
      setProgress(prev => {
        // Cap at 95% to leave room for real completion
        if (prev >= 95) {
          return prev;
        }
        
        // Use different increment speeds based on backend response
        let increment = 1;
        
        return Math.min(prev + increment, 95);
      });
    }, 800);
  };

  const stopFakeProgress = () => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  };

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
    // Reset input value to allow selecting the same file again
    e.target.value = "";
  }, [handleFileSelect]);

  // Enhanced upload handler with smooth fake progress
  const handleAnalyze = useCallback(async (fileToUpload: File) => {
    setStatus("uploading");
    setProgress(0);
    setProcessingProgress(0);
    setError(null);
    setCurrentStep("Preparing upload...");
    hasBackendResponseRef.current = false;

    // Start fake progress tracker
    startFakeProgress();

    const formData = new FormData();
    formData.append("file", fileToUpload);

    try {
      let uploadCompleted = false;
      let hasTransitionedToProcessing = false;

      // Enhanced SSE upload with smooth progress handling
      await api.uploadWithSSE(
        "/api/v1/projects/upload-document",
        formData,
        (uploadProgressValue) => {
          // Handle upload completion
          if (uploadProgressValue >= 100 && !uploadCompleted) {
            setStatus("upload_complete");
            setCurrentStep("Upload complete, starting analysis...");
            uploadCompleted = true;
          }
        },
        (data) => {
          console.log("SSE Message received:", data);
          if (data.status === "processing") {
            hasBackendResponseRef.current = true; // Mark backend response received
            const backendProgress = data.progress || 0;
            
            // Smooth transition from upload to processing
            if (!hasTransitionedToProcessing && backendProgress >= 5) {
              if (!uploadCompleted) {
                setStatus("upload_complete");
              }
              hasTransitionedToProcessing = true;
            }

            // Only update progress if backend progress is higher than current
            setProgress(prev => {
              if (backendProgress > prev) {
                // Stop fake progress temporarily and restart with slower speed
                stopFakeProgress();
                setTimeout(() => {
                  startFakeProgress();
                }, 500);
                return backendProgress;
              }
              return prev; // Don't go backward
            });

            setProcessingProgress(backendProgress);
            
            // Update current step message
            if (data.message) {
              setCurrentStep(data.message);
            }

            // Handle phase-based status updates
            if (data.phase) {
              switch (data.phase) {
                case "upload":
                  setStatus("uploading");
                  break;
                case "upload_complete":
                  setStatus("upload_complete");
                  uploadCompleted = true;
                  break;
                case "parsing":
                  setStatus("parsing");
                  setCurrentStep("Extracting text and analyzing structure...");
                  break;
                case "classifying":
                  setStatus("classifying");
                  setCurrentStep("AI is analyzing your domain expertise...");
                  break;
                case "saving":
                  setStatus("saving");
                  setCurrentStep("Saving results to database...");
                  break;
                default:
                  break;
              }
            } else {
              // Fallback: infer phase from message content
              const message = data.message?.toLowerCase() || "";
              if (message.includes("classifying") || message.includes("classification") || message.includes("domain")) {
                setStatus("classifying");
              } else if (message.includes("extracting") || message.includes("extraction") || message.includes("parsing")) {
                setStatus("parsing");
              } else if (message.includes("saving") || message.includes("database")) {
                setStatus("saving");
              } else if (message.includes("upload") && !uploadCompleted) {
                setStatus("uploading");
              }
            }
          } else if (data.status === "complete") {
            // Handle successful completion
            stopFakeProgress();
            setProgress(100);
            setProcessingProgress(100);
            setStatus("completed");
            setCurrentStep("Analysis complete!");
            
            const result = data.result;
            const classification = result.classified_domain?.overall_classification || "";
            const confidence = (result.classified_domain?.confidence || 0) * 100;
            
            setClassificationData({
              classified: classification,
              confidence,
              resumeId: result.resume_id,
            });
            setSelectedDomain(classification);
            setShowClassificationModal(true);
            toast.success("Resume uploaded and analyzed successfully!");
            
          } else if (data.status === "error") {
            // Handle errors
            stopFakeProgress();
            setStatus("error");
            const errorMessage = data.message || "An unknown error occurred during processing.";
            setError(errorMessage);
            setCurrentStep("Processing failed");
            toast.error(errorMessage);
          }
        }
      );
    } catch (error: any) {
      stopFakeProgress();
      console.error("Upload error:", error);
      setStatus("error");
      let errorMessage = "Failed to upload and analyze resume";
      
      if (error.message) {
        if (error.message.includes("401") || error.message.includes("Unauthorized")) {
          errorMessage = "Authentication failed. Please log in again.";
          // Optional: redirect to login after a delay
          setTimeout(() => {
            router.push("/sign-in");
          }, 3000);
        } else if (error.message.includes("413") || error.message.includes("too large")) {
          errorMessage = "File size too large. Please upload a smaller file.";
        } else if (error.message.includes("415") || error.message.includes("Unsupported")) {
          errorMessage = "Unsupported file type. Please upload a PDF, DOCX, PNG, or JPG file.";
        } else {
          errorMessage = error.message;
        }
      }
      
      setError(errorMessage);
      setCurrentStep("Upload failed");
      toast.error(errorMessage);
    }
  }, [router]);

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

  // Handle final analysis with domain confirmation
  const handleFinalAnalysis = useCallback(async () => {
    if (!classificationData) return;

    try {
      setIsUpdatingDomain(true);
      
      // Only update domain if it was changed from AI classification
      if (selectedDomain !== classificationData.classified) {
        const updateResponse = await api.put(
          `/api/v1/projects/resume/${classificationData.resumeId}`,
          { classified_domain: selectedDomain }
        );
        
        if (!updateResponse.data?.success) {
          throw new Error("Failed to update domain classification");
        }
        
        toast.success(`Domain updated to ${selectedDomain}`);
      }
      
      // Navigate to analysis page
      toast.success("Redirecting to analysis...");
      router.push(`/analyze/${classificationData.resumeId}`);
      
    } catch (error: any) {
      console.error("Failed to update domain:", error);
      const errorMessage = error.response?.data?.message || error.message || "Failed to update domain";
      toast.error(errorMessage);
    } finally {
      setIsUpdatingDomain(false);
    }
  }, [classificationData, selectedDomain, router]);

  // Remove selected file and reset state
  const handleRemoveFile = useCallback(() => {
    setFile(null);
    setResumeFile(null);
    setError(null);
    setStatus("idle");
    setProgress(0);
    setProcessingProgress(0);
    setCurrentStep("");
    // Stop fake progress
    stopFakeProgress();
    hasBackendResponseRef.current = false;
  }, [setResumeFile]);

  // Retry upload functionality
  const handleRetry = useCallback(() => {
    if (file) {
      setError(null);
      setStatus("idle");
      setProgress(0);
      setProcessingProgress(0);
      setCurrentStep("");
      hasBackendResponseRef.current = false;
      handleAnalyze(file);
    }
  }, [file, handleAnalyze]);

  // Cleanup effect
  React.useEffect(() => {
    return () => {
      stopFakeProgress();
    };
  }, []);

  // Get current status message
  const getStatusMessage = () => {
    if (currentStep) return currentStep;
    return PROCESSING_STEPS[status]?.description || "";
  };

  // Helper function to get step completion status
  const getStepStatus = (stepKey: UploadStatus) => {
    const stepOrder = ["uploading", "upload_complete", "parsing", "classifying", "saving"];
    const currentIndex = stepOrder.indexOf(status);
    const stepIndex = stepOrder.indexOf(stepKey);
    
    if (currentIndex === -1) return "pending";
    if (stepIndex < currentIndex) return "completed";
    if (stepIndex === currentIndex) return "current";
    return "pending";
  };

  const isProcessing = ["uploading", "upload_complete", "parsing", "classifying", "saving"].includes(status);
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
        {/* Enhanced Processing Overlay */}
        {isProcessing && (
          <div className="fixed inset-0 z-40 grid place-items-center bg-background/90 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-6 animate-in fade-in zoom-in duration-500 bg-card p-8 rounded-xl border-2 max-w-lg w-full mx-4 shadow-2xl">
              <div className="relative">
                <img
                  src="/images/resume-scan.gif"
                  alt="Processing resume"
                  className="h-32 w-32 object-contain opacity-90"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-background/20 to-transparent rounded-full" />
              </div>
              
              <div className="text-center space-y-4 w-full">
                {/* Current Status Header */}
                <div className="flex items-center justify-center gap-3">
                  <div className="text-primary animate-pulse">
                    {PROCESSING_STEPS[status]?.icon}
                  </div>
                  <p className="text-xl font-semibold">{getStatusMessage()}</p>
                </div>

                {/* Overall Progress */}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Overall Progress</span>
                    <span className="text-muted-foreground font-mono">{Math.round(progress)}%</span>
                  </div>
                  <Progress value={progress} className="w-full h-3" />
                </div>

                {/* Enhanced Processing Steps Grid */}
                <div className="grid grid-cols-2 gap-3 text-xs mt-6">
                  {Object.entries(PROCESSING_STEPS).slice(1, -1).map(([key, step]) => {
                    const stepStatus = getStepStatus(key as UploadStatus);
                    
                    return (
                      <div
                        key={key}
                        className={`flex items-center gap-2 p-3 rounded-lg border transition-all duration-300 ${
                          stepStatus === "current"
                            ? "bg-primary/15 text-primary border-primary/30 shadow-md"
                            : stepStatus === "completed"
                            ? "bg-green-50 text-green-700 border-green-200 dark:bg-green-950/50 dark:text-green-400 dark:border-green-800"
                            : "text-muted-foreground border-border/50 bg-muted/20"
                        }`}
                      >
                        <div className={`${stepStatus === "current" ? "animate-pulse" : ""}`}>
                          {step.icon}
                        </div>
                        <span className="font-medium">{step.name}</span>
                        {stepStatus === "completed" && (
                          <CheckCircle className="w-3 h-3 ml-auto text-green-600" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Upload Form */}
        <form onSubmit={handleSubmit} className="w-full max-w-3xl space-y-8">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-muted-foreground">
              Upload Your Resume
            </label>
            
            {file ? (
              // Selected File Display
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
                      <span>•</span>
                      <span className="text-green-600 font-medium">✓ Valid</span>
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
              // Upload Drop Zone
              <div
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                className={`
                  border-2 border-dashed rounded-lg h-64 sm:h-72 
                  flex flex-col items-center justify-center gap-4 
                  cursor-pointer transition-all duration-300
                  ${dragging 
                    ? "border-primary bg-primary/10 scale-[1.02] shadow-lg" 
                    : "border-border hover:border-primary/50 hover:bg-muted/5"
                  }
                `}
              >
                <div className="text-center space-y-4">
                  <div className={`mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center transition-all duration-300 ${
                    dragging ? "scale-110 bg-primary/20" : ""
                  }`}>
                    <UploadCloud className={`w-6 h-6 text-primary transition-all duration-300 ${
                      dragging ? "scale-110" : ""
                    }`} />
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
                {status === "error" && file && (
                  <Button variant="outline" size="sm" onClick={handleRetry}>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry
                  </Button>
                )}
              </AlertDescription>
            </Alert>
          )}

          {/* Success Message */}
          {status === "completed" && !error && (
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
                {PROCESSING_STEPS[status]?.name || "Processing"}...
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

      {/* Enhanced Classification Modal */}
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
                  Our AI has analyzed your resume and skills
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
                    <span className={`text-sm font-medium ${
                      classificationData.confidence >= 80 
                        ? "text-green-600" 
                        : classificationData.confidence >= 60 
                        ? "text-yellow-600" 
                        : "text-orange-600"
                    }`}>
                      {classificationData.confidence.toFixed(1)}%
                    </span>
                  </div>
                  <Progress 
                    value={classificationData.confidence} 
                    className="h-2"
                  />
                </div>
              </div>

              {/* Confidence Level Indicator */}
              <div className="text-xs text-muted-foreground text-center">
                {classificationData.confidence >= 80 
                  ? "High confidence classification" 
                  : classificationData.confidence >= 60 
                  ? "Medium confidence - please review" 
                  : "Low confidence - manual selection recommended"
                }
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

              {/* Domain Change Warning */}
              {selectedDomain && selectedDomain !== classificationData.classified && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-xs">
                    You've selected a different domain than the AI recommendation. 
                    This will update your analysis results.
                  </AlertDescription>
                </Alert>
              )}

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

              <p className="text-sm text-muted-foreground text-center leading-relaxed">
                By analyzing your resume, you consent to AICommunity, IIT Bombay using your data to improve our AI models.
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </main>
  );
};

export default UploadPage;