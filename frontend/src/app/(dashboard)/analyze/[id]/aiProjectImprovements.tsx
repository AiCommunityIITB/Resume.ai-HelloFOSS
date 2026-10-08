"use client";
import React, { useState, useEffect, useRef } from "react";
import api from "@/lib/api";
import {
  Lightbulb,
  Target,
  TrendingUp,
  Star,
  CheckCircle,
  AlertCircle,
  Sparkles,
  ChevronDown,
  ChevronUp,
  X,
  Code,
} from "lucide-react";
import { createPortal } from "react-dom";

interface ProjectImprovement {
  project_title: string;
  domain?: string;
  percentile?: number;
  similar_projects_count?: number;
  improvements: {
    enhanced_bullet_points?: string[];
    key_improvements?: string[];
    suggested_technologies?: { name: string; reason: string }[];
    error?: string;
  };
}

const ProjectImprovementCard = ({
  project,
  isExpanded,
  onToggle,
}: {
  project: ProjectImprovement;
  isExpanded: boolean;
  onToggle: (expanded: boolean) => void;
}) => {
  // Debug logging
  console.log("ProjectImprovementCard - project:", project);
  console.log("ProjectImprovementCard - isExpanded:", isExpanded);

  if (project.improvements?.error) {
    return (
      <div className="bg-slate-800/60 p-6 rounded-2xl border border-red-500/30">
        <div className="flex items-center gap-4">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <h4 className="font-bold text-white text-lg">
            {project.project_title}
          </h4>
        </div>
        <p className="text-red-300 mt-2">{project.improvements.error}</p>
      </div>
    );
  }

  if (!project.improvements) {
    return (
      <div className="bg-slate-800/60 p-6 rounded-2xl border border-red-500/30">
        <div className="flex items-center gap-4">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <h4 className="font-bold text-white text-lg">
            {project.project_title}
          </h4>
        </div>
        <p className="text-red-300 mt-2">
          No improvements available for this project.
        </p>
      </div>
    );
  }

  // Safely extract improvements data
  const enhancedBulletPoints =
    project.improvements.enhanced_bullet_points || [];
  const keyImprovements = project.improvements.key_improvements || [];
  const suggestedTechnologies =
    project.improvements.suggested_technologies || [];

  // Calculate improvement counts for the header
  const improvementCounts = {
    bullets: enhancedBulletPoints.length,
    improvements: keyImprovements.length,
    technologies: suggestedTechnologies.length,
  };

  const totalImprovements =
    improvementCounts.bullets +
    improvementCounts.improvements +
    improvementCounts.technologies;

  return (
    <div
      className="group relative bg-gradient-to-br from-green-900/20 via-cyan-900/20 to-teal-900/20 rounded-2xl border border-cyan-500/30 hover:border-cyan-400/50 transition-all duration-300"
      onClick={() => onToggle(!isExpanded)}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-green-600/5 via-cyan-600/5 to-teal-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

      <button
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        console.log("Toggle button clicked for:", project.project_title);
        onToggle(!isExpanded);
      }}
      className="w-full p-6 text-left hover:bg-slate-800/30 transition-all duration-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
      type="button"
      >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
        <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-teal-600 rounded-2xl flex items-center justify-center border border-cyan-400/30 shadow-lg">
          <Lightbulb className="w-6 h-6 text-white" />
        </div>
        <div>
          <h4 className="font-bold text-white text-xl mb-1">
          {project.project_title}
          </h4>
          <div className="flex items-center gap-4 text-sm text-slate-400">
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 bg-cyan-400 rounded-full"></div>
            {totalImprovements} improvements available
          </span>
          {project.domain && (
            <span className="flex items-center gap-1">
            <Code className="w-3 h-3 text-blue-400" />
            {project.domain}
            </span>
          )}
          </div>
        </div>
        </div>
        <div className="flex items-center gap-3">
        <span className="text-xs px-2 py-1 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
          {isExpanded ? "Expanded" : "Click to expand"}
        </span>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-slate-400 group-hover:text-white transition-colors" />
        ) : (
          <ChevronDown className="w-5 h-5 text-slate-400 group-hover:text-white transition-colors" />
        )}
        </div>
      </div>
      </button>

      {isExpanded && (
      <div className="px-6 pb-6 border-t border-slate-700/50">
        <div className="space-y-6 mt-6">
        {enhancedBulletPoints.length > 0 && (
          <div>
          <h5 className="text-teal-300 font-bold text-lg mb-3 flex items-center gap-2">
            <Target className="w-4 h-4" /> Enhanced Bullet Points
          </h5>
          <div className="space-y-3">
            {enhancedBulletPoints.map((item, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 p-3 bg-slate-800/60 rounded-lg border border-teal-500/30 hover:border-teal-400/50 transition-all duration-200"
            >
              <CheckCircle className="w-5 h-5 text-teal-400 mt-0.5 flex-shrink-0" />
              <p className="text-slate-200 leading-relaxed">
              {typeof item === "string"
                ? item
                  .replace(/^\*\*/, "")
                  .replace(/\*\*$/, "")
                  .replace(/^- /, "")
                : String(item)}
              </p>
            </div>
            ))}
          </div>
          </div>
        )}

        {keyImprovements.length > 0 && (
          <div>
          <h5 className="text-cyan-300 font-bold text-lg mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" /> Key Improvements
          </h5>
          <div className="space-y-3">
            {keyImprovements.map((item, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 p-3 bg-slate-800/60 rounded-lg border border-cyan-500/30 hover:border-cyan-400/50 transition-all duration-200"
            >
              <CheckCircle className="w-5 h-5 text-cyan-400 mt-0.5 flex-shrink-0" />
              <p className="text-slate-200 leading-relaxed">
              {typeof item === "string"
                ? item
                  .replace(/^\*\*/, "")
                  .replace(/\*\*$/, "")
                  .replace(/^- /, "")
                : String(item)}
              </p>
            </div>
            ))}
          </div>
          </div>
        )}

        {suggestedTechnologies.length > 0 && (
          <div>
          <h5 className="text-green-300 font-bold text-lg mb-3 flex items-center gap-2">
            <Star className="w-4 h-4" /> Suggested Technologies
          </h5>
          <div className="space-y-3">
            {suggestedTechnologies.map((tech, idx) => (
            <div
              key={idx}
              className="p-3 bg-slate-800/60 rounded-lg border border-green-500/30 hover:border-green-400/50 transition-all duration-200"
            >
              <p className="font-semibold text-white">
              {typeof tech === "object" && tech.name
                ? tech.name
                : String(tech)}
              </p>
              {typeof tech === "object" && tech.reason && (
              <p className="text-sm text-slate-300">{tech.reason}</p>
              )}
            </div>
            ))}
          </div>
          </div>
        )}

        {totalImprovements === 0 && (
          <div className="text-center p-6">
          <AlertCircle className="w-8 h-8 text-slate-400 mx-auto mb-2" />
          <p className="text-slate-400">
            No specific improvements available for this project.
          </p>
          </div>
        )}
        </div>
      </div>
      )}
    </div>
  );
};

const Notification = ({
  message,
  isVisible,
  onClose,
}: {
  message: string;
  isVisible: boolean;
  onClose: () => void;
}) => {
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        onClose();
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [isVisible, onClose]);

  if (!isVisible) return null;

  return createPortal(
    <div className="fixed top-4 right-4 z-[10000] animate-in slide-in-from-right duration-300">
      <div className="bg-slate-800/95 backdrop-blur-xl border border-slate-700/50 rounded-xl p-4 shadow-2xl max-w-sm">
        <div className="flex items-start justify-between">
          <div className="flex items-center">
            <div className="w-8 h-8 bg-green-500/20 rounded-lg mr-3 flex items-center justify-center flex-shrink-0">
              <CheckCircle className="w-4 h-4 text-green-400" />
            </div>
            <p className="text-sm text-white font-medium">{message}</p>
          </div>
          <button
            onClick={onClose}
            className="ml-2 p-1 hover:bg-slate-700/50 rounded-lg transition-colors duration-200 flex-shrink-0"
          >
            <X className="w-4 h-4 text-slate-400 hover:text-white" />
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

const AIProjectImprovements = ({ resumeId }: { resumeId: string }) => {
  const [projects, setProjects] = useState<ProjectImprovement[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [expandedProjects, setExpandedProjects] = useState<Set<number>>(
    new Set()
  );
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState(0);
  const [currentProject, setCurrentProject] = useState<string>("");
  const [showNotification, setShowNotification] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const hasBackendResponseRef = useRef<boolean>(false); // Track if we've received backend responses

  // Enhanced fake progress function with different speeds based on backend response
  const startFakeProgress = () => {
    // Clear any existing interval
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }

    progressIntervalRef.current = setInterval(() => {
      setLoadingProgress((prev) => {
        // Cap at 95% to leave room for real completion
        if (prev >= 95) {
          return prev;
        }

        // Use smaller increments if we've received backend responses
        let increment;
        if (hasBackendResponseRef.current) {
          // Much smaller increments after receiving backend response
          increment = prev < 80 ? 0.3 : prev < 90 ? 0.2 : 0.1;
        } else {
          // Normal increments before backend response
          increment = prev < 30 ? 2 : prev < 60 ? 1.5 : 0.5;
        }

        return Math.min(prev + increment, 95);
      });
    }, 800); // Slower intervals after backend response
  };

  const stopFakeProgress = () => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  };

  // Fixed toggle function with better logging
  const toggleProject = (index: number, expanded: boolean) => {
    setExpandedProjects((prev) => {
      const newSet = new Set(prev);
      if (expanded) newSet.add(index);
      else newSet.delete(index);
      return newSet;
    });
  };

  const expandAll = () => {
    console.log("Expanding all projects");
    setExpandedProjects(new Set(projects.map((_, index) => index)));
  };

  const collapseAll = () => {
    console.log("Collapsing all projects");
    setExpandedProjects(new Set());
  };

  // Fixed data processing function
  const processProjectData = (rawData: any[]): ProjectImprovement[] => {
    console.log("Processing raw project data:", rawData);

    return rawData.map((item: any, index: number) => {
      console.log(`Processing project ${index}:`, item);

      // Handle different possible data structures
      let improvementsData = item.improvements;

      // If improvements is nested (like improvements.improvements)
      if (
        improvementsData &&
        typeof improvementsData === "object" &&
        improvementsData.improvements
      ) {
        improvementsData = improvementsData.improvements;
      }

      // Ensure we have a valid object
      if (!improvementsData || typeof improvementsData !== "object") {
        improvementsData = {};
      }

      const processedProject: ProjectImprovement = {
        project_title: item.project_title || `Project ${index + 1}`,
        domain: item.domain,
        percentile: item.percentile,
        similar_projects_count: item.similar_projects_count,
        improvements: {
          enhanced_bullet_points: Array.isArray(
            improvementsData.enhanced_bullet_points
          )
            ? improvementsData.enhanced_bullet_points
            : [],
          key_improvements: Array.isArray(improvementsData.key_improvements)
            ? improvementsData.key_improvements
            : [],
          suggested_technologies: Array.isArray(
            improvementsData.suggested_technologies
          )
            ? improvementsData.suggested_technologies
            : [],
          error: improvementsData.error,
        },
      };

      console.log(`Processed project ${index}:`, processedProject);
      return processedProject;
    });
  };

  // Updated fetchImprovements with non-regressive progress
  const fetchImprovements = async () => {
    if (!resumeId || loading) return;

    setLoading(true);
    setError(null);
    setHasStarted(true);
    setLoadingProgress(0);
    setCurrentStage(0);
    setCurrentProject("");
    setProjects([]);
    setExpandedProjects(new Set());
    hasBackendResponseRef.current = false; // Reset backend response flag

    // Start fake progress immediately
    startFakeProgress();

    // Clean up previous EventSource
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      // Use the api.createSSEConnection method
      const eventSource = api.createSSEConnection(
        `/api/v1/projects/resume/${resumeId}/project-improvements`,
        { withCredentials: true }
      );
      eventSourceRef.current = eventSource;

      eventSource.onopen = (event) => {
        console.log("EventSource connection opened:", event);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("Received SSE data:", data);

          if (data.status === "processing" || data.status === "starting") {
            hasBackendResponseRef.current = true; // Mark that we've received backend response

            // Only update progress if backend progress is higher than current
            const backendProgress = data.progress || 0;
            setLoadingProgress((prev) => {
              if (backendProgress > prev) {
                return backendProgress;
              }
              return prev; // Don't go backward
            });

            setCurrentStage(data.stage_index || 0);
            setCurrentProject(data.current_project || "");

            // Restart fake progress with slower increments
            stopFakeProgress();
            setTimeout(() => {
              startFakeProgress();
            }, 500);
          } else if (data.status === "complete") {
            stopFakeProgress();
            setLoadingProgress(100);

            // Process the data correctly
            const rawProjects = data.data || [];
            console.log("Raw projects from backend:", rawProjects);

            const processedProjects = processProjectData(rawProjects);
            console.log("Processed projects:", processedProjects);

            setProjects(processedProjects);
            setShowNotification(true);
            setLoading(false);

            // Automatically expand the first project if it has improvements
            if (processedProjects.length > 0) {
              setExpandedProjects(new Set([0]));
            }

            eventSource.close();
          } else if (data.status === "error") {
            stopFakeProgress();
            console.error("Error from backend:", data.message);
            setError(data.message || "An error occurred");
            setLoading(false);
            setHasStarted(false);
            eventSource.close();
          }
        } catch (parseError) {
          console.error("Error parsing SSE data:", parseError, event.data);
        }
      };

      eventSource.onerror = (error) => {
        stopFakeProgress();
        console.error(
          "EventSource connection error. State:",
          eventSource.readyState,
          "Error:",
          error
        );

        if (eventSource.readyState === EventSource.CLOSED) {
          console.log("EventSource connection was closed");
        } else {
          setError("Connection failed. Please try again.");
        }

        setLoading(false);
        setHasStarted(false);
        eventSource.close();
      };
    } catch (error: any) {
      stopFakeProgress();
      console.error("Error creating EventSource:", error);
      let errorMessage = "Failed to start connection. Please try again.";

      // Handle specific authentication errors
      if (error.message && error.message.includes("No access token found")) {
        errorMessage = "Authentication failed. Please log in again.";
      }

      setError(errorMessage);
      setLoading(false);
      setHasStarted(false);
    }
  };

  // Alternative method using regular API call (fallback) with fake progress
  const fetchImprovementsWithRegularAPI = async () => {
    if (!resumeId || loading) return;

    setLoading(true);
    setError(null);
    setHasStarted(true);
    setLoadingProgress(0);
    setProjects([]);
    setExpandedProjects(new Set());
    hasBackendResponseRef.current = false;

    // Start fake progress
    startFakeProgress();

    try {
      setCurrentStage(0);
      setCurrentProject("Fetching project data...");

      const response = await api.get(
        `/api/v1/projects/resume/${resumeId}/project-improvements`
      );

      hasBackendResponseRef.current = true;
      setCurrentStage(1);
      setCurrentProject("Processing improvements...");

      if (response.data && response.data.success) {
        const rawProjects = response.data.data || [];
        const processedProjects = processProjectData(rawProjects);

        stopFakeProgress();
        setLoadingProgress(100);
        setCurrentStage(3);
        setProjects(processedProjects);
        setShowNotification(true);
        setLoading(false);

        // Automatically expand the first project if it has improvements
        if (processedProjects.length > 0) {
          setExpandedProjects(new Set([0]));
        }
      } else {
        throw new Error(
          response.data?.message || "Failed to fetch improvements"
        );
      }
    } catch (error: any) {
      stopFakeProgress();
      console.error("Error fetching improvements:", error);
      let errorMessage = "Failed to fetch improvements. Please try again.";

      if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }

      setError(errorMessage);
      setLoading(false);
      setHasStarted(false);
    }
  };

  const getStageInfo = () => {
    const stages = [
      { name: "Loading Projects", color: "blue" },
      { name: "Analyzing Projects", color: "purple" },
      { name: "Generating Improvements", color: "green" },
      { name: "Finalizing Results", color: "teal" },
    ];
    return stages[currentStage] || stages[0];
  };

  const closeNotification = () => {
    setShowNotification(false);
  };

  // Updated cleanup effect
  useEffect(() => {
    return () => {
      stopFakeProgress(); // Clean up fake progress interval
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Debug logging for expand/collapse state
  useEffect(() => {
    console.log("Projects updated:", projects.length);
    console.log("Expanded projects:", Array.from(expandedProjects));
  }, [projects, expandedProjects]);

  // Show initial button if analysis hasn't started
  if (!hasStarted) {
    return (
      <div className="text-center p-8 bg-slate-800/60 rounded-2xl border border-slate-700/50">
        <div className="mb-4">
          <Sparkles className="w-12 h-12 text-cyan-400 mx-auto mb-3" />
          <h3 className="text-xl font-bold text-white mb-2">
            AI-Powered Project Improvements
          </h3>
          <p className="text-slate-400 mb-6">
            Get personalized suggestions to enhance your project descriptions
            with AI analysis
          </p>
        </div>
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={fetchImprovements}
            disabled={loading}
            className="inline-flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-cyan-500 to-teal-600 text-white font-semibold rounded-xl hover:from-cyan-600 hover:to-teal-700 transition-all duration-300 shadow-lg hover:shadow-cyan-500/25 transform hover:scale-105"
          >
            <Lightbulb className="w-5 h-5" />
            Analyze Projects for Improvements
          </button>
        </div>
      </div>
    );
  }

  // Show loading state with streaming progress
  if (loading) {
    return (
      <div className="text-center p-8 bg-slate-800/60 rounded-2xl border border-slate-700/50">
        <div className="flex justify-center items-center mb-4">
          <div className="w-8 h-8 border-4 border-cyan-500 border-solid border-t-transparent rounded-full animate-spin"></div>
        </div>
        <div className="space-y-4">
          <h3 className="text-xl font-bold text-white">Analyzing Projects</h3>
          <p className="text-slate-300">
            AI is analyzing your projects for improvements...
          </p>

          {/* Progress Bar with Percentage */}
          <div className="max-w-md mx-auto mb-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-slate-400">Progress</span>
              <span className="text-sm text-slate-400">
                {Math.round(loadingProgress)}%
              </span>
            </div>
            <div className="w-full bg-slate-700/50 rounded-full h-3 overflow-hidden">
              <div
                className="bg-gradient-to-r from-cyan-500 to-teal-500 h-3 rounded-full transition-all duration-1000 ease-out"
                style={{ width: `${loadingProgress}%` }}
              />
            </div>
          </div>

          {/* Current Stage Display */}
          <div className="mb-6">
            <div
              className={`inline-flex items-center px-4 py-2 rounded-lg border text-sm font-medium ${
                getStageInfo().color === "blue"
                  ? "bg-blue-500/20 border-blue-500/30 text-blue-300"
                  : getStageInfo().color === "purple"
                  ? "bg-purple-500/20 border-purple-500/30 text-purple-300"
                  : getStageInfo().color === "green"
                  ? "bg-green-500/20 border-green-500/30 text-green-300"
                  : "bg-teal-500/20 border-teal-500/30 text-teal-300"
              }`}
            >
              <div className="w-2 h-2 rounded-full bg-current mr-2 animate-pulse" />
              {getStageInfo().name}
            </div>
          </div>

          {/* Current Project Being Processed */}
          {currentProject && (
            <div className="mb-4">
              <p className="text-slate-400 text-sm">Currently analyzing:</p>
              <p className="text-white font-medium">{currentProject}</p>
            </div>
          )}

          {/* Loading Stages Progress */}
          <div className="grid grid-cols-4 gap-2 text-xs">
            <div
              className={`p-2 rounded-lg border transition-all duration-300 ${
                currentStage >= 0
                  ? "bg-blue-500/20 border-blue-500/30 text-blue-300"
                  : "bg-slate-700/30 border-slate-600/30 text-slate-500"
              }`}
            >
              Loading
            </div>
            <div
              className={`p-2 rounded-lg border transition-all duration-300 ${
                currentStage >= 1
                  ? "bg-purple-500/20 border-purple-500/30 text-purple-300"
                  : "bg-slate-700/30 border-slate-600/30 text-slate-500"
              }`}
            >
              Analyzing
            </div>
            <div
              className={`p-2 rounded-lg border transition-all duration-300 ${
                currentStage >= 2
                  ? "bg-green-500/20 border-green-500/30 text-green-300"
                  : "bg-slate-700/30 border-slate-600/30 text-slate-500"
              }`}
            >
              Improving
            </div>
            <div
              className={`p-2 rounded-lg border transition-all duration-300 ${
                currentStage >= 3
                  ? "bg-teal-500/20 border-teal-500/30 text-teal-300"
                  : "bg-slate-700/30 border-slate-600/30 text-slate-500"
              }`}
            >
              Finalizing
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="text-center p-8 bg-slate-800/60 rounded-2xl border border-red-500/30">
        <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-3" />
        <h3 className="text-xl font-bold text-white mb-2">Analysis Failed</h3>
        <p className="text-red-400 mb-4">{error}</p>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={fetchImprovements}
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors duration-200"
          >
            <Lightbulb className="w-4 h-4" />
            Retry with Streaming
          </button>
          <button
            onClick={fetchImprovementsWithRegularAPI}
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-600 text-white font-medium rounded-lg hover:bg-slate-700 transition-colors duration-200"
          >
            <Target className="w-4 h-4" />
            Try Regular API
          </button>
        </div>
      </div>
    );
  }

  // Show empty state
  if (projects.length === 0) {
    return (
      <div className="text-center p-8 bg-slate-800/60 rounded-2xl border border-slate-700/50">
        <Lightbulb className="w-8 h-8 text-slate-400 mx-auto mb-3" />
        <h3 className="text-xl font-bold text-white mb-2">
          No Improvements Found
        </h3>
        <p className="text-slate-400 mb-4">
          No project improvements are available at the moment.
        </p>
        <button
          onClick={fetchImprovements}
          className="inline-flex items-center gap-2 px-4 py-2 bg-slate-600 text-white font-medium rounded-lg hover:bg-slate-700 transition-colors duration-200"
        >
          <Lightbulb className="w-4 h-4" />
          Retry Analysis
        </button>
      </div>
    );
  }

  // Show results with collapsible projects
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-bold text-white flex items-center gap-3">
          <Lightbulb className="text-cyan-400" />
          AI-Powered Project Improvements
        </h3>
        <div className="flex items-center gap-2">
          {projects.length > 1 && (
            <React.Fragment>
              <button
                onClick={expandAll}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 hover:text-white transition-colors duration-200"
              >
                <ChevronDown className="w-4 h-4" />
                Expand All
              </button>
              <button
                onClick={collapseAll}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 hover:text-white transition-colors duration-200"
              >
                <ChevronUp className="w-4 h-4" />
                Collapse All
              </button>
            </React.Fragment>
          )}
          <button
            onClick={fetchImprovements}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 hover:text-white transition-colors duration-200"
          >
            <Sparkles className="w-4 h-4" />
            Re-analyze
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {projects.map((project, index) => {
          const isExpanded = expandedProjects.has(index);
          console.log(
            `Rendering project ${index} (${project.project_title}), expanded: ${isExpanded}`
          );

          return (
            <ProjectImprovementCard
              key={`project-${resumeId}-${index}-${project.project_title}`}
              project={project}
              isExpanded={expandedProjects.has(index)}
              onToggle={(expanded) => toggleProject(index, expanded)}
            />
          );
        })}
      </div>

      {/* Notification */}
      <Notification
        message="Project improvements generated successfully!"
        isVisible={showNotification}
        onClose={closeNotification}
      />
    </div>
  );
};

export default AIProjectImprovements;
