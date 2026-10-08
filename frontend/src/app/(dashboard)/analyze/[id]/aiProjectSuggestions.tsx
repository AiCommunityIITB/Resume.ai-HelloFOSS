import React, { useState, useEffect, useRef } from 'react';
import { Clock, Code, Target, TrendingUp, ChevronRight, X, Sparkles, ChevronLeft, CheckCircle, AlertCircle } from 'lucide-react';
import api from '@/lib/api';
import { createPortal } from 'react-dom';

// Types
interface ProjectSuggestion {
  project_title: string;
  project_description: string;
  difficulty_level: string;
  estimated_duration: string;
  primary_technologies: string[];
  new_technologies_to_learn: string[];
  industry_relevance: string;
  portfolio_impact: string;
}

interface CategoryAnalysis {
  user_projects_count: number;
  average_score: number;
  suggested_projects: ProjectSuggestion[];
}

interface SimilarProjectsResponse {
  ai_project_suggestions: Record<string, CategoryAnalysis>;
}

const ProjectCard = ({ project }: { project: ProjectSuggestion }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
      case 'beginner': return 'bg-green-500/20 text-green-300 border-green-500/30';
      case 'intermediate': return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
      case 'advanced': return 'bg-red-500/20 text-red-300 border-red-500/30';
      default: return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
    }
  };

  return (
    <div className="bg-slate-800/60 rounded-xl border border-slate-700/40 p-4 hover:bg-slate-800/80 transition-all duration-300">
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <h5 className="font-bold text-white text-lg leading-tight pr-4">
          {project.project_title}
        </h5>
        <span className={`text-xs px-2 py-1 rounded-full border font-medium whitespace-nowrap ${getDifficultyColor(project.difficulty_level)}`}>
          {project.difficulty_level}
        </span>
      </div>

      {/* Quick Info */}
      <div className="flex flex-wrap gap-3 mb-3 text-sm">
        <div className="flex items-center text-slate-400">
          <Clock className="w-3 h-3 mr-1" />
          <span className="text-xs">{project.estimated_duration}</span>
        </div>
        <div className="flex items-center text-slate-400">
          <Code className="w-3 h-3 mr-1" />
          <span className="text-xs">{project.primary_technologies.length} Technologies</span>
        </div>
      </div>

      {/* Description */}
      <p className="text-slate-300 text-sm leading-relaxed mb-3">
        {project.project_description}
      </p>

      {/* Technologies - Show All */}
      <div className="mb-3">
        <div className="flex flex-wrap gap-1">
          {project.primary_technologies.map((tech, index) => (
            <span
              key={index}
              className="text-xs px-2 py-1 bg-blue-500/15 text-blue-300 rounded-md border border-blue-500/25"
            >
              {tech}
            </span>
          ))}
        </div>
      </div>

      {/* Expandable Section */}
      {isExpanded && (
        <div className="border-t border-slate-700/50 pt-3 mt-3 space-y-3">
          {/* New Technologies */}
          {project.new_technologies_to_learn.length > 0 && (
            <div>
              <h6 className="text-xs font-semibold text-white mb-2 flex items-center">
                <Target className="w-3 h-3 mr-1 text-purple-400" />
                New Technologies
              </h6>
              <div className="flex flex-wrap gap-1">
                {project.new_technologies_to_learn.map((tech, index) => (
                  <span
                    key={index}
                    className="text-xs px-2 py-1 bg-purple-500/15 text-purple-300 rounded-md border border-purple-500/25"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Industry Relevance */}
          <div>
            <h6 className="text-xs font-semibold text-white mb-2 flex items-center">
              <TrendingUp className="w-3 h-3 mr-1 text-green-400" />
              Industry Impact
            </h6>
            <p className="text-xs text-slate-300 leading-relaxed">
              {project.industry_relevance}
            </p>
          </div>

          {/* Portfolio Impact */}
          <div>
            <h6 className="text-xs font-semibold text-white mb-2">Portfolio Value</h6>
            <p className="text-xs text-slate-300 leading-relaxed">
              {project.portfolio_impact}
            </p>
          </div>
        </div>
      )}

      {/* Expand/Collapse Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="mt-3 w-full flex items-center justify-center text-xs text-blue-400 hover:text-blue-300 transition-colors duration-200 py-2 border-t border-slate-700/30"
      >
        <span>{isExpanded ? 'Show Less' : 'Show More'}</span>
        <ChevronRight className={`w-3 h-3 ml-1 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`} />
      </button>
    </div>
  );
};

const Notification = ({ 
  message, 
  isVisible, 
  onClose 
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

const AIProjectCarousel = ({ 
  isOpen, 
  onClose, 
  similarProjects, 
  onRefresh 
}: {
  isOpen: boolean;
  onClose: () => void;
  similarProjects: SimilarProjectsResponse | null;
  onRefresh: () => void;
}) => {
  const [currentSlide, setCurrentSlide] = useState(0);
  const categories = similarProjects ? Object.entries(similarProjects.ai_project_suggestions) : [];

  const nextSlide = () => {
    setCurrentSlide((prev) => (prev + 1) % categories.length);
  };

  const prevSlide = () => {
    setCurrentSlide((prev) => (prev - 1 + categories.length) % categories.length);
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') nextSlide();
      if (e.key === 'ArrowLeft') prevSlide();
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, categories.length]);

  useEffect(() => {
    if (isOpen) {
      setCurrentSlide(0);
    }
  }, [isOpen]);

  if (!isOpen || !similarProjects || categories.length === 0) return null;

  const [currentCategory, currentAnalysis] = categories[currentSlide];

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm" 
        onClick={onClose} 
      />
      
      {/* Carousel Container */}
      <div className="relative w-full max-w-6xl max-h-[90vh] bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 shadow-2xl rounded-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700/50 flex-shrink-0">
          <div className="flex items-center">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg mr-3 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-bold text-white">AI Project Suggestions</h2>
          </div>
          <div className="flex items-center gap-4">
            {/* Slide Indicator */}
            <div className="flex items-center gap-2">
              {categories.map((_, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentSlide(index)}
                  className={`w-2 h-2 rounded-full transition-all duration-200 ${
                    index === currentSlide ? 'bg-blue-500 w-6' : 'bg-slate-600 hover:bg-slate-500'
                  }`}
                />
              ))}
            </div>
            <span className="text-sm text-slate-400">
              {currentSlide + 1} / {categories.length}
            </span>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-800/60 rounded-lg transition-colors duration-200"
            >
              <X className="w-5 h-5 text-slate-400 hover:text-white" />
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex items-stretch min-h-0">
          {/* Previous Button */}
          <div className="flex items-center p-4">
            <button
              onClick={prevSlide}
              disabled={categories.length <= 1}
              className="p-3 hover:bg-slate-800/60 rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-6 h-6 text-slate-400 hover:text-white" />
            </button>
          </div>

          {/* Slide Content */}
          <div className="flex-1 py-6 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-600 scrollbar-track-transparent">
            <div className="px-6 space-y-6">
              {/* Category Header */}
              <div className="bg-gradient-to-r from-slate-900/80 to-slate-800/80 rounded-xl border border-slate-700/50 p-6">
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="font-bold text-white text-2xl mb-2">
                      {currentCategory}
                    </h3>
                    <p className="text-slate-400">
                      Based on {currentAnalysis.user_projects_count} existing projects
                    </p>
                  </div>
                  <div className="flex gap-6">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-400">{currentAnalysis.average_score}</div>
                      <div className="text-sm text-slate-500">Avg Score</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-400">{currentAnalysis.user_projects_count}</div>
                      <div className="text-sm text-slate-500">Projects</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Project Cards */}
              <div className="grid gap-4 pb-6">
                {currentAnalysis.error ? (
                  <div className="text-center p-8 text-slate-400 bg-slate-800/50 rounded-lg">
                    <AlertCircle className="mx-auto w-8 h-8 text-amber-400 mb-3" />
                    <h4 className="font-semibold text-white mb-2">Suggestions Unavailable</h4>
                    {currentAnalysis.error}
                  </div>
                ) : Array.isArray(currentAnalysis.suggested_projects) && currentAnalysis.suggested_projects.length > 0 ? (
                  currentAnalysis.suggested_projects.map((project, index) => (
                    <ProjectCard key={index} project={project} />
                  ))
                ) : (
                  <div className="text-center p-8 text-slate-400">
                    No project suggestions available for this category. This might happen if the AI couldn't generate relevant suggestions based on your projects.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Next Button */}
          <div className="flex items-center p-4">
            <button
              onClick={nextSlide}
              disabled={categories.length <= 1}
              className="p-3 hover:bg-slate-800/60 rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-6 h-6 text-slate-400 hover:text-white" />
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-slate-700/50 p-4 text-center flex-shrink-0">
          <button
            onClick={onRefresh}
            className="text-sm text-slate-400 hover:text-slate-300 transition-colors duration-200 px-4 py-2 border border-slate-700/50 rounded-lg hover:bg-slate-800/50"
          >
            Refresh Suggestions
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

const AIProjectSuggestions = ({ resumeId }: { resumeId: string }) => {
  const [similarProjects, setSimilarProjects] = useState<SimilarProjectsResponse | null>(null);
  const [similarProjectsLoading, setSimilarProjectsLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState(0);
  const [hasRequested, setHasRequested] = useState(false);
  const [isCarouselOpen, setIsCarouselOpen] = useState(false);
  const [showNotification, setShowNotification] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Improved fake progress function with stage-aware progression
  const startFakeProgress = () => {
    // Clear any existing interval
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }

    progressIntervalRef.current = setInterval(() => {
      setLoadingProgress(prev => {
        // Cap fake progress at 95% to leave room for real completion
        if (prev >= 99) {
          return prev;
        }
        
        // Dynamic increment based on current progress for smooth progression
        let increment;
        if (prev < 15) {
          increment = 1.8; // Faster start
        } else if (prev < 35) {
          increment = 1.2; // Medium-fast early stage
        } else if (prev < 60) {
          increment = 0.8; // Slower middle stage
        } else if (prev < 80) {
          increment = 0.5; // Slower late stage
        } else {
          increment = 0.2; // Very slow final stage
        }
        
        return Math.min(prev + increment, 99);
      });
    }, 1200); // Smooth 1.2 second intervals
  };

  // Stop fake progress function
  const stopFakeProgress = () => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  };

  // Fallback function for regular API (you'll need to implement this)
  const fetchSimilarProjectsWithRegularAPI = async () => {
    setSimilarProjectsLoading(true);
    setErrorMessage(null);
    
    try {
      const response = await api.get(`/api/v1/projects/resume/${resumeId}/find-similar-projects`);
      setSimilarProjects(response.data);
      setShowNotification(true);
      setSimilarProjectsLoading(false);
    } catch (error: any) {
      console.error("Regular API error:", error);
      setErrorMessage(error.response?.data?.message || "Failed to generate suggestions");
      setSimilarProjectsLoading(false);
    }
  };

  // Main fetch function with improved progress handling
  const fetchSimilarProjects = async () => {
    if (similarProjectsLoading) return;

    setSimilarProjectsLoading(true);
    setHasRequested(true);
    setLoadingProgress(0);
    setCurrentStage(0);
    setSimilarProjects(null);
    setErrorMessage(null);

    // Start fake progress immediately
    startFakeProgress();

    // Clean up previous EventSource
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const eventSource = api.createSSEConnection(
        `/api/v1/projects/resume/${resumeId}/find-similar-projects`,
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

          if (data.status === 'processing' || data.status === 'starting') {
            // Update stage without interrupting fake progress
            setCurrentStage(data.stage_index || 0);
            
            // Only update progress if server progress is significantly higher
            // This maintains smooth fake progress while respecting real updates
            setLoadingProgress(prev => {
              const serverProgress = data.progress || 0;
              // Only jump to server progress if it's at least 5% higher than current
              if (serverProgress > prev + 5) {
                return Math.max(prev, serverProgress);
              }
              return prev; // Keep fake progress moving
            });
            
            // Keep fake progress running throughout all stages
            
          } else if (data.status === 'complete') {
            stopFakeProgress();
            setLoadingProgress(100);
            setSimilarProjects(data.data || null);
            setShowNotification(true);
            setSimilarProjectsLoading(false);
            eventSource.close();
          } else if (data.status === 'error') {
            stopFakeProgress();
            console.error("Error from backend:", data.message);
            setErrorMessage(data.message || "An error occurred");
            setSimilarProjects(null);
            setHasRequested(false);
            setSimilarProjectsLoading(false);
            eventSource.close();
          }
        } catch (parseError) {
          console.error("Error parsing SSE data:", parseError, event.data);
        }
      };

      eventSource.onerror = (error) => {
        stopFakeProgress();
        console.error("EventSource connection error. State:", eventSource.readyState, "Error:", error);
        
        if (eventSource.readyState === EventSource.CLOSED) {
          console.log("EventSource connection was closed");
        } else {
          setErrorMessage("Connection failed. Please try again.");
        }
        
        setSimilarProjects(null);
        setHasRequested(false);
        setSimilarProjectsLoading(false);
        eventSource.close();
      };

    } catch (error: any) {
      stopFakeProgress();
      console.error("Error creating EventSource:", error);
      let errorMessage = "Failed to start connection. Please try again.";
      
      if (error.message && error.message.includes("No access token found")) {
        errorMessage = "Authentication failed. Please log in again.";
      }
      
      setErrorMessage(errorMessage);
      setSimilarProjectsLoading(false);
      setHasRequested(false);
    }
  };

  const openCarousel = () => {
    if (!similarProjects) return;
    setIsCarouselOpen(true);
    document.body.style.overflow = 'hidden';
  };

  const closeCarousel = () => {
    setIsCarouselOpen(false);
    document.body.style.overflow = 'unset';
  };

  const closeNotification = () => {
    setShowNotification(false);
  };

  const handleRefresh = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    fetchSimilarProjects();
  };

  const getStageInfo = () => {
    const stages = [
      { name: 'Parsing Skills', color: 'blue' },
      { name: 'AI Analysis', color: 'purple' },
      { name: 'Generating Ideas', color: 'green' }
    ];
    return stages[currentStage] || stages[0];
  };

  useEffect(() => {
    return () => {
      document.body.style.overflow = 'unset';
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      stopFakeProgress(); // Clean up progress interval
    };
  }, []);

  return (
    <>
      <div className="space-y-6">
        <h3 className="text-2xl font-bold text-white mb-6 flex items-center">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg mr-3 flex items-center justify-center">
            <Target className="w-5 h-5 text-white" />
          </div>
          AI Project Suggestions
        </h3>
        
        {!hasRequested ? (
          <div className="bg-gradient-to-br from-slate-900/60 to-slate-800/60 rounded-2xl border border-slate-700/50 p-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl mx-auto mb-4 flex items-center justify-center">
                <Code className="w-8 h-8 text-white" />
              </div>
              <h4 className="text-xl font-semibold text-white mb-3">
                Ready for Your Next Challenge?
              </h4>
              <p className="text-slate-400 mb-6 max-w-md mx-auto leading-relaxed">
                Get personalized AI-powered project suggestions tailored to your skills and experience level
              </p>
              <div className="flex items-center justify-center gap-4">
                <button
                  onClick={fetchSimilarProjects}
                  disabled={similarProjectsLoading}
                  className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-xl transition-all duration-300 font-semibold shadow-lg hover:shadow-blue-500/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3"
                >
                  {similarProjectsLoading ? (
                    <>
                      <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                      Generating Suggestions...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5" />
                      Generate AI Suggestions
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        ) : similarProjectsLoading ? (
          <div className="bg-gradient-to-br from-slate-900/60 to-slate-800/60 rounded-2xl border border-slate-700/50 p-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl mx-auto mb-4 flex items-center justify-center">
                <div className="animate-spin w-8 h-8 border-2 border-white border-t-transparent rounded-full" />
              </div>
              <h4 className="text-xl font-semibold text-white mb-3">
                Generating AI Suggestions...
              </h4>
              <p className="text-slate-400 mb-6 max-w-md mx-auto leading-relaxed">
                Our AI is analyzing your profile to create personalized project recommendations
              </p>
              
              <div className="max-w-md mx-auto mb-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-slate-400">Progress</span>
                  <span className="text-sm text-slate-400">{Math.round(loadingProgress)}%</span>
                </div>
                <div className="w-full bg-slate-700/50 rounded-full h-3 overflow-hidden">
                  <div 
                    className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-1000 ease-out"
                    style={{ width: `${loadingProgress}%` }}
                  />
                </div>
              </div>

              <div className="mb-6">
                <div className={`inline-flex items-center px-4 py-2 rounded-lg border text-sm font-medium ${
                  getStageInfo().color === 'blue' 
                    ? 'bg-blue-500/20 border-blue-500/30 text-blue-300'
                    : getStageInfo().color === 'purple'
                    ? 'bg-purple-500/20 border-purple-500/30 text-purple-300'
                    : 'bg-green-500/20 border-green-500/30 text-green-300'
                }`}>
                  <div className="w-2 h-2 rounded-full bg-current mr-2 animate-pulse" />
                  {getStageInfo().name}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 text-xs">
                <div className={`p-2 rounded-lg border transition-all duration-300 ${
                  currentStage >= 0
                    ? 'bg-blue-500/20 border-blue-500/30 text-blue-300' 
                    : 'bg-slate-700/30 border-slate-600/30 text-slate-500'
                }`}>
                  Parsing Skills
                </div>
                <div className={`p-2 rounded-lg border transition-all duration-300 ${
                  currentStage >= 1
                    ? 'bg-purple-500/20 border-purple-500/30 text-purple-300' 
                    : 'bg-slate-700/30 border-slate-600/30 text-slate-500'
                }`}>
                  AI Analysis
                </div>
                <div className={`p-2 rounded-lg border transition-all duration-300 ${
                  currentStage >= 2
                    ? 'bg-green-500/20 border-green-500/30 text-green-300' 
                    : 'bg-slate-700/30 border-slate-600/30 text-slate-500'
                }`}>
                  Generating Ideas
                </div>
              </div>
            </div>
          </div>
        ) : errorMessage ? (
          <div className="bg-gradient-to-br from-red-900/20 to-red-800/20 rounded-2xl border border-red-700/50 p-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-red-500/20 rounded-2xl mx-auto mb-4 flex items-center justify-center">
                <AlertCircle className="w-8 h-8 text-red-400" />
              </div>
              <h4 className="text-xl font-semibold text-white mb-3">
                Generation Failed
              </h4>
              <p className="text-slate-400 mb-6 max-w-md mx-auto leading-relaxed">
                {errorMessage}
              </p>
              <div className="flex items-center justify-center gap-3">
                <button
                  onClick={handleRefresh}
                  className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl transition-all duration-300 font-medium"
                >
                  Retry with Streaming
                </button>
                <button
                  onClick={fetchSimilarProjectsWithRegularAPI}
                  className="px-6 py-2 bg-slate-600 hover:bg-slate-700 text-white rounded-xl transition-all duration-300 font-medium"
                >
                  Try Regular API
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-gradient-to-br from-slate-900/60 to-slate-800/60 rounded-2xl border border-slate-700/50 p-6">
            <div className="text-center">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl mx-auto mb-4 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <h4 className="text-lg font-semibold text-white mb-3">
                AI Suggestions Generated!
              </h4>
              <p className="text-slate-400 mb-4">
                Your personalized project suggestions are ready to explore
              </p>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={openCarousel}
                  disabled={!similarProjects}
                  className="px-6 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-xl transition-all duration-300 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  View AI Suggestions
                </button>
                <button
                  onClick={handleRefresh}
                  className="px-6 py-2 bg-slate-700/50 hover:bg-slate-700/70 text-slate-300 hover:text-white rounded-xl transition-all duration-300 font-medium border border-slate-600/50"
                >
                  Regenerate
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <Notification
        message="AI project suggestions generated successfully!"
        isVisible={showNotification}
        onClose={closeNotification}
      />

      <AIProjectCarousel
        isOpen={isCarouselOpen}
        onClose={closeCarousel}
        similarProjects={similarProjects}
        onRefresh={handleRefresh}
      />
    </>
  );
};

export default AIProjectSuggestions;
