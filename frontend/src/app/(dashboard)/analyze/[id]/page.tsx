"use client";
import React, { useState, useEffect, useRef } from "react";
import {
  ChevronDown,
  ChevronUp,
  CheckCircle,
  AlertCircle,
  ArrowLeft,
  Lightbulb,
  Target,
  TrendingUp,
  Shield,
  Star,
  Focus,
  BarChart,
  MessageSquare,
} from "lucide-react";
import ResumePreviewSlider from "./resumePreviewSlider";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { useParams } from "next/navigation";
import api from "@/lib/api";
import AIProjectSuggestions from "./aiProjectSuggestions";
import AIProjectImprovements from "./aiProjectImprovements";
import ScoreCard from "./overallScore";

const FeedbackPage = () => {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});
  const [resumeDetails, setResumeDetails] = useState<any>(null);
  const [isGenerating, setIsGenerating] = useState(true);

  // ---------------- TYPES ----------------
  interface Tip {
    type: "good" | "improve";
    tip: string;
    explanation: string;
  }

  interface Project {
    type: string;
    project: string;
    score: number;
    explanation: string;
  }

  interface POR {
    type: string;
    title: string;
    similarityScore: number | null;
    explanation: string;
    enhancedSuggestions?: {
      enhanced_por: {
        title: string;
        bullet_points: string[];
        key_improvements: string[];
      };
      enhancement_summary: {
        primary_focus: string;
        strength_areas: string[];
        impact_score: number;
      };
    };
    hasEnhancement: boolean;
  }

  interface ScoreSection {
    score: number;
    tips?: Tip[];
  }

  interface ProjectSection {
    score: number;
    projects: Project[];
    similarProjects?: any;
  }

  interface PORSection {
    pors: POR[];
  }

  // ---- API RESPONSE TYPES ----
  interface ProjectApi {
    project_title: string;
    scores: {
      weighted_score: number;
      technical_complexity: number;
      technology_stack_relevance: number;
      innovation_uniqueness: number;
      project_scope_completeness: number;
    };
    percentile: number;
  }

  interface PORApi {
    por_index: number;
    user_por: {
      title: string;
      organization: string;
      duration: string;
      responsibilities: string[];
      achievements: string[];
    };
    processing_status: string;
    error: null | string;
    similar_pors?: {
      target_por: any;
      top_k_similar: { similarity_score: number }[];
      total_pors_analyzed: number;
    };
    similar_pors_count: number;
    gemini_suggestions?: string;
    enhanced_suggestions?: {
      enhanced_por: {
        title: string;
        bullet_points: string[];
        key_improvements: string[];
      };
      enhancement_summary: {
        primary_focus: string;
        strength_areas: string[];
        impact_score: number;
      };
    };
    has_enhancement: boolean;
    processing_time: number;
  }

  // ---------------- STATE ----------------
  const params = useParams();
  const resumeId = params.id as string;
  const hasFetched = useRef(false);

  const [projects, setProjects] = useState<ProjectApi[]>([]);
  const [por, setPor] = useState<{ por_analyses: PORApi[] } | null>(null);
  const [whitespace, setWhitespace] = useState<{ whitespace_score: number } | null>(null);
  const [similarProjects, setSimilarProjects] = useState<any>(null);
  const [workExScore, setWorkExScore] = useState<any>(null);
  const [achievementsScore, setAchievementsScore] = useState<any>(null);

  const [loading, setLoading] = useState(true);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [porLoading, setPorLoading] = useState(true);
  const [whitespaceLoading, setWhitespaceLoading] = useState(true);
  const [similarProjectsLoading, setSimilarProjectsLoading] = useState(true);
  const [workExLoading, setWorkExLoading] = useState(true);
  const [achievementsLoading, setAchievementsLoading] = useState(true);

  // ---------------- API CALLS ----------------
  useEffect(() => {
    const fetchResumeDetails = async () => {
      if (!resumeId) return;
      try {
        const res = await api.get(`/api/v1/projects/resume/${resumeId}`);
        setResumeDetails(res.data.data);
      } catch (error) {
        console.error("Failed to fetch resume details:", error);
      } finally {
        setIsGenerating(false);
      }
    };

    fetchResumeDetails();
  }, [resumeId]);

  useEffect(() => {
    if (!resumeId || hasFetched.current) return;

    const fetchAllData = async () => {
      hasFetched.current = true;
      setLoading(true);

      try {
        console.log("Starting first batch of API calls...");
        await Promise.all([
          api
            .post(`/api/v1/projects/resume/${resumeId}/score-projects`)
            .then((res) => {
              console.log("Projects API:", res.data);
              setProjects(res.data.data || []);
            })
            .finally(() => setProjectsLoading(false)),

          api
            .post(`/api/v1/projects/resume/${resumeId}/por-similarity-analysis`)
            .then((res) => {
              console.log("POR API:", res.data);
              setPor(res.data.data || null);
            })
            .finally(() => setPorLoading(false)),

          api
            .post(`/api/v1/projects/resume/${resumeId}/score-workex`)
            .then((res) => {
              console.log("WorkEx Score API:", res.data);
              setWorkExScore(res.data.data || null);
            })
            .finally(() => setWorkExLoading(false)),

          api
            .post(`/api/v1/projects/resume/${resumeId}/classify-achievements`)
            .then((res) => {
              console.log("Achievements Score API:", res.data);
              setAchievementsScore(res.data.data || null);
            })
            .finally(() => setAchievementsLoading(false)),
        ]);

        console.log("First batch completed. Starting whitespace analysis...");

        await api
          .get(`/api/v1/projects/resume/${resumeId}/whitespace-score`)
          .then((res) => {
            console.log("Whitespace API:", res.data);
            setWhitespace(res.data.data || null);
          })
          .finally(() => setWhitespaceLoading(false));

        console.log("All API calls completed.");
      } catch (error) {
        console.error("Failed to fetch resume data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, [resumeId]);

  // ---------------- HELPER FUNCTIONS ----------------
  const calculateOverallProjectScore = () => {
    if (projects.length === 0) return 0;
    const totalPercentile = projects.reduce(
      (sum, project) => sum + project.percentile,
      0
    );
    return Math.round(totalPercentile / projects.length);
  };

  const getMaxWorkExScore = () => {
    if (
      !workExScore ||
      !Array.isArray(workExScore) ||
      workExScore.length === 0
    ) {
      return 0;
    }
    return Math.max(...workExScore.map((item) => item.percentile || 0));
  };

  // Manage expanded states for individual PORs
  const [expandedPORs, setExpandedPORs] = useState<Set<number>>(new Set());

  const togglePOR = (index: number) => {
    setExpandedPORs((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  // POR Card component with individual collapsible control
  const PORCard = ({ por, index }: { por: POR; index: number }) => {
    const isExpanded = expandedPORs.has(index);
    return (
      <div className="space-y-6 border border-slate-700/50 rounded-2xl p-6 bg-slate-900/40">
        <button
          onClick={() => togglePOR(index)}
          className="w-full flex items-center justify-between text-left"
        >
          <div className="flex items-center gap-4">
            <div
              className={`w-3 h-3 rounded-full ${por.hasEnhancement ? "bg-emerald-400" : "bg-slate-400"}`}
            />
            <h4 className="font-semibold text-white text-lg truncate">
              {por.title}
            </h4>
          </div>
          <div className="flex items-center gap-3 text-slate-400">
            {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </div>
        </button>

        <div
          className={`transition-all duration-500 ease-in-out overflow-hidden ${
            isExpanded
              ? "max-h-[2000px] opacity-100"
              : "max-h-0 opacity-0"
          }`}
        >
          <div className="mt-4 space-y-6">
            {por.hasEnhancement && por.enhancedSuggestions && (
              <div className="group relative bg-gradient-to-br from-blue-900/20 via-purple-900/20 to-indigo-900/20 rounded-2xl border border-blue-500/30 hover:border-blue-400/50 transition-all duration-300 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-purple-600/5 to-indigo-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                <div className="relative p-8">
                  {/* Header Section */}
                  <div className="flex items-start justify-between mb-6">
                    <div className="flex items-center gap-4">
                      <div className="relative">
                        <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center border border-blue-400/30 shadow-lg">
                          <Lightbulb className="w-6 h-6 text-white" />
                        </div>
                        <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-slate-900 flex items-center justify-center">
                          <CheckCircle className="w-3 h-3 text-white" />
                        </div>
                      </div>
                      <div>
                        <h4 className="font-bold text-white text-xl mb-1">Enhanced POR</h4>
                        <p className="text-slate-400 text-sm">AI-powered improvements for maximum impact</p>
                      </div>
                    </div>

                    {por.enhancedSuggestions.enhancement_summary?.impact_score && (
                      <div className="flex flex-col items-center gap-2">
                        <div className="relative w-16 h-16">
                          <svg className="w-16 h-16 transform -rotate-90" viewBox="0 0 36 36">
                            <path
                              className="text-slate-700"
                              strokeDasharray="100, 100"
                              strokeWidth="2"
                              fill="none"
                              stroke="currentColor"
                              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            />
                            <path
                              className="text-blue-400 transition-all duration-1000 ease-out"
                              strokeDasharray={`${por.enhancedSuggestions.enhancement_summary.impact_score * 10}, 100`}
                              strokeWidth="2"
                              strokeLinecap="round"
                              fill="none"
                              stroke="currentColor"
                              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            />
                          </svg>
                          <div className="absolute inset-0 flex items-center justify-center">
                            <span className="text-xl font-bold text-white">
                              {por.enhancedSuggestions.enhancement_summary.impact_score}
                            </span>
                          </div>
                        </div>
                        <span className="text-xs text-slate-400 font-medium">Impact Score</span>
                      </div>
                    )}
                  </div>

                  {/* Enhanced Content Grid */}
                  <div className="space-y-6">
                    {/* Enhanced Title */}
                    {por.enhancedSuggestions.enhanced_por?.title &&
                      por.enhancedSuggestions.enhanced_por.title !== por.title && (
                        <div className="group/title">
                          <div className="flex items-center gap-3 mb-3">
                            <div className="w-8 h-8 bg-emerald-500/20 rounded-lg flex items-center justify-center border border-emerald-500/30">
                              <Target className="w-4 h-4 text-emerald-400" />
                            </div>
                            <h5 className="text-emerald-300 font-bold text-lg">Enhanced Title</h5>
                            <div className="h-px bg-gradient-to-r from-emerald-500/50 to-transparent flex-1" />
                          </div>
                          <div className="bg-gradient-to-br from-slate-800/60 to-slate-700/60 p-6 rounded-xl border border-emerald-500/30 hover:border-emerald-400/50 transition-all duration-300">
                            <p className="text-white font-medium leading-relaxed">
                              {por.enhancedSuggestions.enhanced_por.title}
                            </p>
                          </div>
                        </div>
                      )}

                    {/* Enhanced Bullet Points */}
                    {por.enhancedSuggestions.enhanced_por?.bullet_points &&
                    Array.isArray(por.enhancedSuggestions.enhanced_por.bullet_points) &&
                    por.enhancedSuggestions.enhanced_por.bullet_points.length > 0 && (
                      <div className="group/bullets">
                        <div className="flex items-center gap-3 mb-4">
                          <div className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center border border-blue-500/30">
                            <TrendingUp className="w-4 h-4 text-blue-400" />
                          </div>
                          <h5 className="text-blue-300 font-bold text-lg">Enhanced Bullet Points</h5>
                          <div className="h-px bg-gradient-to-r from-blue-500/50 to-transparent flex-1" />
                        </div>
                        <div className="space-y-3">
                          {por.enhancedSuggestions.enhanced_por.bullet_points.map((bullet, idx) => (
                            <div
                              key={idx}
                              className="group/bullet bg-gradient-to-br from-slate-800/60 to-slate-700/60 p-4 rounded-xl border border-blue-500/30 hover:border-blue-400/50 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/10"
                            >
                              <div className="flex items-start gap-4">
                                <div className="w-6 h-6 bg-blue-500/20 rounded-full flex items-center justify-center border border-blue-500/30 mt-1 flex-shrink-0">
                                  <div className="w-2 h-2 bg-blue-400 rounded-full group-hover/bullet:animate-pulse" />
                                </div>
                                <p className="text-slate-200 leading-relaxed flex-1">{bullet}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Key Improvements Made */}
                    {por.enhancedSuggestions.enhanced_por.key_improvements &&
                    Array.isArray(por.enhancedSuggestions.enhanced_por.key_improvements) &&
                    por.enhancedSuggestions.enhanced_por.key_improvements.length > 0 && (
                      <div className="group/improvements">
                        <div className="flex items-center gap-3 mb-4">
                          <div className="w-8 h-8 bg-amber-500/20 rounded-lg flex items-center justify-center border border-amber-500/30">
                            <Star className="w-4 h-4 text-amber-400" />
                          </div>
                          <h5 className="text-amber-300 font-bold text-lg">Key Improvements Made</h5>
                          <div className="h-px bg-gradient-to-r from-amber-500/50 to-transparent flex-1" />
                        </div>
                        <div className="grid gap-3">
                          {por.enhancedSuggestions.enhanced_por.key_improvements.map((improvement, idx) => (
                            <div
                              key={idx}
                              className="flex items-start gap-3 p-4 bg-gradient-to-br from-amber-500/10 to-orange-500/5 rounded-lg border border-amber-500/20 hover:border-amber-400/30 transition-all duration-200"
                            >
                              <div className="w-5 h-5 bg-amber-500/20 rounded-full flex items-center justify-center mt-0.5 flex-shrink-0">
                                <CheckCircle className="w-3 h-3 text-amber-400" />
                              </div>
                              <p className="text-slate-300 leading-relaxed">{improvement}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Enhancement Summary */}
                    {por.enhancedSuggestions.enhancement_summary && (
                      <div className="border-t border-slate-700/50 pt-6">
                        <div className="flex items-center gap-3 mb-4">
                          <div className="w-8 h-8 bg-purple-500/20 rounded-lg flex items-center justify-center border border-purple-500/30">
                            <BarChart className="w-4 h-4 text-purple-400" />
                          </div>
                          <h5 className="text-purple-300 font-bold text-lg">Enhancement Summary</h5>
                          <div className="h-px bg-gradient-to-r from-purple-500/50 to-transparent flex-1" />
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          {por.enhancedSuggestions.enhancement_summary.primary_focus && (
                            <div className="bg-purple-500/5 p-4 rounded-xl border border-purple-500/20">
                              <div className="flex items-center gap-2 mb-2">
                                <Focus className="w-4 h-4 text-purple-400" />
                                <span className="text-purple-300 font-semibold text-sm">Primary Focus</span>
                              </div>
                              <p className="text-white leading-relaxed">{por.enhancedSuggestions.enhancement_summary.primary_focus}</p>
                            </div>
                          )}

                          {por.enhancedSuggestions.enhancement_summary.strength_areas &&
                          Array.isArray(por.enhancedSuggestions.enhancement_summary.strength_areas) &&
                          por.enhancedSuggestions.enhancement_summary.strength_areas.length > 0 && (
                            <div className="bg-purple-500/5 p-4 rounded-xl border border-purple-500/20">
                              <div className="flex items-center gap-2 mb-3">
                                <Shield className="w-4 h-4 text-purple-400" />
                                <span className="text-purple-300 font-semibold text-sm">Strength Areas</span>
                              </div>
                              <div className="space-y-2">
                                {por.enhancedSuggestions.enhancement_summary.strength_areas.map((area, idx) => (
                                  <div key={idx} className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 bg-purple-400 rounded-full flex-shrink-0" />
                                    <span className="text-slate-300 text-sm">{area}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ---------------- SECTION NAME MAPPING ----------------
  const getSectionDisplayName = (key: string): string => {
    const sectionNames: Record<string, string> = {
      whitespaceScore: "Whitespace & Formatting",
      scholasticAchievementsScore: "Scholastic Achievements",
      workExScore: "Work Experience",
      ProjectScore: "Project Analysis",
      PORimprovements: "Position of Responsibility",
    };

    return sectionNames[key] || key;
  };

  // ---------------- CALCULATE OVERALL SCORE ----------------
  const calculateOverallScore = () => {
    const weights = {
      whitespace: 0.2,
      achievements: 0.25,
      workEx: 0.3,
      projects: 0.25,
    };

    const whitespaceScore = whitespace?.whitespace_score ?? 0;
    const achievementsScoreValue = achievementsScore?.average_score
      ? Math.round(80 + achievementsScore.average_score / 5)
      : 80;
    const workExScoreValue = getMaxWorkExScore();
    const projectsScore = calculateOverallProjectScore();

    const overallScore = Math.round(
      whitespaceScore * weights.whitespace +
        achievementsScoreValue * weights.achievements +
        workExScoreValue * weights.workEx +
        projectsScore * weights.projects
    );

    return Math.max(0, Math.min(100, overallScore));
  };

  // ---------------- FEEDBACK DATA ----------------
  const resData = {
    feedback: {
      overAllScore: calculateOverallScore(),
      whitespaceScore: {
        score: whitespace?.whitespace_score ?? 0,
      },
      scholasticAchievementsScore: {
        score: achievementsScore?.average_score
          ? Math.round(80 + achievementsScore.average_score / 5)
          : 80,
        tips: [
          {
            type: "improve",
            tip: "Add technical skills section",
            explanation:
              "Include a dedicated section highlighting your programming languages, frameworks, and tools.",
          },
          {
            type: "improve",
            tip: "Group skills by category",
            explanation:
              "Organize skills into categories like 'Programming Languages', 'Frameworks', 'Tools', etc.",
          },
          {
            type: "improve",
            tip: "Include proficiency levels",
            explanation:
              "Consider indicating your proficiency level for each skill (e.g., Expert, Intermediate, Beginner).",
          },
        ],
      },
      workExScore: {
        score: getMaxWorkExScore(),
        tips: [
          {
            type: "good",
            tip: "Logical section organization",
            explanation:
              "Your resume follows a clear, logical structure that's easy to follow.",
          },
          {
            type: "improve",
            tip: "Optimize section spacing",
            explanation:
              "Consider adjusting white space between sections for better visual balance.",
          },
          {
            type: "good",
            tip: "Consistent formatting",
            explanation:
              "Consistent use of fonts, sizes, and formatting throughout the document.",
          },
        ],
      },
      ProjectScore: {
        score: calculateOverallProjectScore(),
        projects: projects.map(
          (p: ProjectApi): Project => ({
            type: "good",
            project: p.project_title,
            score: p.percentile,
            explanation: `
            Technical Complexity: ${p.scores.technical_complexity}, 
            Relevance: ${p.scores.technology_stack_relevance}, 
            Innovation: ${p.scores.innovation_uniqueness}, 
            Scope: ${p.scores.project_scope_completeness}
          `,
          })
        ),
        similarProjects: similarProjects,
      },
      PORimprovements: {
        pors:
          por?.por_analyses.map(
            (p: PORApi): POR => ({
              type: "improve",
              title: p.user_por.title,
              similarityScore:
                p.similar_pors?.top_k_similar?.[0]?.similarity_score || null,
              explanation: p.gemini_suggestions || "No suggestions available",
              enhancedSuggestions: p.enhanced_suggestions,
              hasEnhancement: p.has_enhancement,
            })
          ) || [],
      },
    },
  };

  type Feedback = typeof resData.feedback;
  type SectionKey = keyof Omit<Feedback, "overAllScore">;

  // ---------------- TOGGLE ----------------
  const toggleSection = (section: SectionKey) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  // ---------------- HELPER FUNCTIONS FOR LOADING STATES ----------------
  const getSectionLoadingState = (key: string) => {
    switch (key) {
      case "ProjectScore":
        return projectsLoading;
      case "PORimprovements":
        return porLoading;
      case "whitespaceScore":
        return whitespaceLoading;
      case "workExScore":
        return workExLoading;
      case "scholasticAchievementsScore":
        return achievementsLoading;
      default:
        return false;
    }
  };

  const getSectionLoadingText = (key: string) => {
    switch (key) {
      case "ProjectScore":
        return "Analyzing projects...";
      case "PORimprovements":
        return "Analyzing positions of responsibility...";
      case "whitespaceScore":
        return "Analyzing whitespace usage...";
      case "workExScore":
        return "Analyzing work experience...";
      case "scholasticAchievementsScore":
        return "Analyzing achievements...";
      default:
        return "Loading...";
    }
  };

  // ---------------- UI COMPONENTS ----------------
  const Spinner = () => (
    <div className="flex justify-center items-center p-4">
      <div className="w-6 h-6 border-4 border-blue-500 border-solid border-t-transparent rounded-full animate-spin"></div>
    </div>
  );

  const SkeletonLoader = () => (
    <div className="space-y-4">
      <div className="h-8 bg-slate-700 rounded w-3/4 animate-pulse"></div>
      <div className="h-4 bg-slate-700 rounded w-full animate-pulse"></div>
      <div className="h-4 bg-slate-700 rounded w-5/6 animate-pulse"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Main Container with proper spacing for header */}
      <div className="container mx-auto px-4 pt-24 pb-12">
        {/* Back Navigation */}
        <div className="mb-6 flex justify-between items-center">
          <Link
            href="/resumes"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors duration-200 group"
          >
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform duration-200" />
            Back to Resumes
          </Link>
        </div>

        {/* Main Grid Layout */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* Resume Preview - Sticky on larger screens */}
          <div className="xl:col-span-1">
            <div className="sticky top-24">
              <ResumePreviewSlider
                resumeId={resumeId}
                fileName={resumeDetails?.filename}
              />
            </div>
          </div>

          {/* Analysis Content */}
          <div className="xl:col-span-2">
            <div className="space-y-8">
              {/* Page Header */}
              <div className="bg-slate-900/80 backdrop-blur-sm rounded-2xl shadow-2xl border border-slate-700/50 p-8">
                <div className="mb-8">
                  <h1 className="text-4xl font-bold text-white mb-3">Resume Analysis</h1>
                  <p className="text-slate-300 text-lg leading-relaxed">
                    Comprehensive analysis of your resume's performance with actionable insights 
                    and optimization recommendations
                  </p>
                </div>

                <ScoreCard score={calculateOverallScore()} loading={loading} />
              </div>

              {/* Analysis Sections */}
              <div className="space-y-6">
                {Object.entries(resData.feedback)
                  .filter(([key]) => key !== "overAllScore")
                  .map(([key, section]) => {
                    const sectionName = getSectionDisplayName(key);
                    const isExpanded = expandedSections[key];
                    const hasScore =
                      typeof section === "object" &&
                      section !== null &&
                      "score" in section;
                    const score = hasScore
                      ? (section as ScoreSection).score
                      : null;

                    const isLoading = getSectionLoadingState(key);
                    const loadingText = getSectionLoadingText(key);

                    // Loading State
                    if (isLoading) {
                      return (
                        <div
                          key={key}
                          className="bg-slate-800/60 backdrop-blur-sm rounded-2xl shadow-lg border border-slate-700/50 p-6"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div className="w-3 h-3 rounded-full bg-slate-400"></div>
                              <span className="font-semibold text-white text-lg">
                                {sectionName}
                              </span>
                            </div>
                            <div className="flex items-center gap-3">
                              <Spinner />
                              <span className="text-slate-400 text-sm">
                                {loadingText}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    }

                    // Non-expandable sections
                    if (
                      key === "workExScore" ||
                      key === "scholasticAchievementsScore" ||
                      key === "whitespaceScore"
                    ) {
                      return (
                        <div
                          key={key}
                          className="bg-slate-800/60 backdrop-blur-sm rounded-xl shadow-lg border border-slate-700/50 p-6 hover:bg-slate-800/80 transition-all duration-200"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div
                                className={`w-3 h-3 rounded-full shadow-sm ${
                                  score !== null
                                    ? score >= 80
                                      ? "bg-emerald-400"
                                      : score >= 60
                                      ? "bg-amber-400"
                                      : "bg-red-400"
                                    : "bg-slate-400"
                                }`}
                              />
                              <span className="font-semibold text-white text-lg">
                                {sectionName}
                              </span>
                            </div>
                            <span
                              className={`text-sm px-3 py-1.5 rounded-full font-semibold border ${
                                score !== null && score >= 80
                                  ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                                  : score !== null && score >= 60
                                  ? "bg-amber-500/15 text-amber-300 border-amber-500/30"
                                  : "bg-red-500/15 text-red-300 border-red-500/30"
                              }`}
                            >
                              {Math.round(score ?? 0)}/100
                            </span>
                          </div>
                        </div>
                      );
                    }

                    // Expandable sections
                    // Special case for PORimprovements to render multiple collapsible PORCards
                    if (key === "PORimprovements" && section && typeof section === "object" && "pors" in section) {
                      return (
                        <div
                          key={key}
                          className="bg-slate-800/60 backdrop-blur-sm rounded-2xl shadow-lg border border-slate-700/50"
                        >
                          {/* Section Header */}
                          <button
                            onClick={() => toggleSection(key as SectionKey)}
                            className="w-full flex items-center justify-between p-6 text-left hover:bg-slate-800/80 transition-all duration-200 rounded-2xl"
                          >
                            <div className="flex items-center gap-4">
                              <div
                                className={`w-3 h-3 rounded-full bg-emerald-400`}
                              ></div>
                              <span className="font-semibold text-white text-lg">
                                {sectionName}
                              </span>
                            </div>
                            <div className="flex items-center gap-3 text-slate-400">
                              {score !== null && (
                                <span className="text-sm px-3 py-1 rounded-full font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                  {score}/100
                                </span>
                              )}
                              {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                            </div>
                          </button>

                          {/* Section Content: Render PORCards if section expanded */}
                          <div
                            className={`transition-all duration-500 ease-in-out overflow-hidden ${
                              isExpanded
                                ? " opacity-100"
                                : "max-h-0 opacity-0"
                            }`}
                          >
                            <div className="space-y-6 px-6 pb-6 border-t border-slate-700/50">
                              {section.pors.map((por: POR, i: number) => (
                                <PORCard key={i} por={por} index={i} />
                              ))}
                            </div>
                          </div>
                        </div>
                      );
                    }

                    // Default fallback for unknown expandable sections
                    return (
                      <div
                        key={key}
                        className="bg-slate-800/60 backdrop-blur-sm rounded-2xl shadow-lg border border-slate-700/50"
                      >
                        {/* Section Header */}
                        <button
                          onClick={() => toggleSection(key as SectionKey)}
                          className="w-full flex items-center justify-between p-6 text-left hover:bg-slate-800/80 transition-all duration-200 rounded-2xl"
                        >
                          <div className="flex items-center gap-4">
                            <div
                              className={`w-3 h-3 rounded-full ${
                                key === "PORimprovements"
                                  ? "bg-emerald-400"
                                  : score !== null
                                  ? score >= 80
                                    ? "bg-emerald-400"
                                    : score >= 60
                                    ? "bg-amber-400"
                                    : "bg-red-400"
                                  : "bg-slate-400"
                              }`}
                            ></div>
                            <span className="font-semibold text-white text-lg">
                              {sectionName}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-slate-400">
                            {score !== null && (
                              <span
                                className={`text-sm px-3 py-1 rounded-full font-medium ${
                                  score >= 80
                                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                    : score >= 60
                                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                                    : "bg-red-500/20 text-red-300 border border-red-500/30"
                                }`}
                              >
                                {score}/100
                              </span>
                            )}
                            {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                          </div>
                        </button>

                        {/* Section Content */}
                        <div
                          className={`transition-all duration-500 ease-in-out overflow-hidden ${
                            isExpanded
                              ? key === "ProjectScore" || key === "PORimprovements"
                                ? "max-h-none opacity-100"  // No height limit for complex sections
                                : "max-h-[2000px] opacity-100"  // Keep limit for simpler sections
                              : "max-h-0 opacity-0"
                          }`}
                        >
                          <div className="px-6 pb-6 border-t border-slate-700/50">
                            <div className="space-y-4 mt-4">
                              {/* Tips */}
                              {typeof section === "object" &&
                                section !== null &&
                                "tips" in section &&
                                Array.isArray((section as ScoreSection).tips) &&
                                (section as ScoreSection).tips!.map(
                                  (tip: Tip, index: number) => (
                                    <div
                                      key={index}
                                      className="flex gap-4 p-4 bg-slate-900/40 rounded-lg border border-slate-700/30 hover:bg-slate-900/60 transition-colors duration-200"
                                    >
                                      <div className="mt-1 flex-shrink-0">
                                        {tip.type === "good" ? (
                                          <div className="w-8 h-8 bg-emerald-500/20 rounded-full flex items-center justify-center border border-emerald-500/30">
                                            <CheckCircle className="w-5 h-5 text-emerald-400" />
                                          </div>
                                        ) : (
                                          <div className="w-8 h-8 bg-amber-500/20 rounded-full flex items-center justify-center border border-amber-500/30">
                                            <AlertCircle className="w-5 h-5 text-amber-400" />
                                          </div>
                                        )}
                                      </div>
                                      <div className="flex-1 min-w-0">
                                        <h4 className="font-semibold text-white mb-2 leading-tight">
                                          {tip.tip}
                                        </h4>
                                        <p className="text-sm text-slate-300 leading-relaxed">
                                          {tip.explanation}
                                        </p>
                                      </div>
                                    </div>
                                  )
                                )}

                              {/* Projects Section */}
                              {key === "ProjectScore" && (
                                <div className="space-y-6">
                                  {/* Projects List */}
                                  <div>
                                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                                      <BarChart className="w-5 h-5" />
                                      Project Analysis Results
                                    </h3>
                                    <div className="space-y-3">
                                      {(section as ProjectSection).projects.map(
                                        (proj: Project, i: number) => (
                                          <div
                                            key={i}
                                            className="p-4 bg-slate-900/40 rounded-lg border border-slate-700/30 hover:bg-slate-900/60 transition-colors duration-200"
                                          >
                                            <div className="flex justify-between items-center mb-2">
                                              <h4 className="font-semibold text-white">
                                                {proj.project}
                                              </h4>
                                              <span className="text-xs px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                                {proj.score}
                                              </span>
                                            </div>
                                            <p className="text-sm text-slate-300">
                                              {proj.explanation}
                                            </p>
                                          </div>
                                        )
                                      )}
                                    </div>
                                  </div>

                                  {/* AI Project Suggestions */}
                                  <div>
                                    <AIProjectSuggestions resumeId={resumeId} />
                                  </div>

                                  {/* AI Project Improvements - Integrated directly here */}
                                  <div className="border-t border-slate-700/50 pt-6">
                                    <AIProjectImprovements resumeId={resumeId} />
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FeedbackPage;