"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { 
  Eye, 
  Download, 
  Trash2, 
  PlusCircle, 
  FileText, 
  Calendar, 
  Loader2, 
  Search,
  Filter,
  AlertCircle,
  RefreshCw,
  SortAsc,
  SortDesc
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner"; // Assuming you're using sonner for toasts

interface Resume {
  resume_id: number;
  filename: string;
  created_at: string;
  classified_domain: string;
}

type SortOption = "name" | "date" | "domain";
type SortDirection = "asc" | "desc";

const ResumesPage = () => {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [filteredResumes, setFilteredResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDomain, setSelectedDomain] = useState<string>("all");
  const [sortBy, setSortBy] = useState<SortOption>("date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [actionLoading, setActionLoading] = useState<{ [key: number]: string }>({});
  const router = useRouter();

  const fetchResumes = useCallback(async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      setError(null);
      
      const response = await api.get("/api/v1/projects/resumes");
      
      if (response.data.success) {
        setResumes(response.data.data.resumes || []);
      } else {
        throw new Error(response.data.message || "Failed to fetch resumes");
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || "An error occurred while fetching resumes";
      setError(errorMessage);
      console.error("Fetch resumes error:", err);
      
      if (!showLoading) {
        toast.error("Failed to refresh resumes");
      }
    } finally {
      if (showLoading) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchResumes();
  }, [fetchResumes]);

  // Filter and sort resumes
  useEffect(() => {
    let filtered = resumes.filter((resume) => {
      const matchesSearch = resume.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          (resume.classified_domain || '').toLowerCase().includes(searchTerm.toLowerCase());
      const matchesDomain = selectedDomain === "all" || 
                          (resume.classified_domain || '').toLowerCase() === selectedDomain.toLowerCase();
      return matchesSearch && matchesDomain;
    });

    // Sort resumes
    filtered.sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case "name":
          comparison = a.filename.localeCompare(b.filename);
          break;
        case "date":
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
        case "domain":
          comparison = (a.classified_domain || '').localeCompare(b.classified_domain || '');
          break;
      }
      
      return sortDirection === "asc" ? comparison : -comparison;
    });

    setFilteredResumes(filtered);
  }, [resumes, searchTerm, selectedDomain, sortBy, sortDirection]);

  const handleView = (resumeId: number) => {
    router.push(`/analyze/${resumeId}`);
  };

  const handleDownload = async (resumeId: number) => {
    const resume = resumes.find((r) => r.resume_id === resumeId);
    if (!resume) {
      toast.error("Resume not found");
      return;
    }

    setActionLoading(prev => ({ ...prev, [resumeId]: "downloading" }));

    try {
      const response = await api.get(
        `/api/v1/projects/resume/${resumeId}/download`,
        {
          responseType: "blob",
          timeout: 30000, // 30 second timeout
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", resume.filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success("Resume downloaded successfully");
    } catch (error: any) {
      console.error("Failed to download resume:", error);
      const errorMessage = error.response?.data?.message || "Failed to download resume";
      toast.error(errorMessage);
    } finally {
      setActionLoading(prev => {
        const newState = { ...prev };
        delete newState[resumeId];
        return newState;
      });
    }
  };

  const handleDelete = async (resumeId: number) => {
    const resume = resumes.find((r) => r.resume_id === resumeId);
    if (!resume) return;

    // Better confirmation dialog
    const confirmed = window.confirm(
      `Are you sure you want to delete "${resume.filename}"?\n\nThis action cannot be undone.`
    );
    
    if (!confirmed) return;

    setActionLoading(prev => ({ ...prev, [resumeId]: "deleting" }));

    try {
      const response = await api.delete(`/api/v1/projects/resume/${resumeId}`);
      
      if (response.data.success) {
        setResumes(resumes.filter((r) => r.resume_id !== resumeId));
        toast.success("Resume deleted successfully");
      } else {
        throw new Error(response.data.message || "Failed to delete resume");
      }
    } catch (error: any) {
      console.error("Failed to delete resume:", error);
      const errorMessage = error.response?.data?.message || "Failed to delete resume";
      toast.error(errorMessage);
    } finally {
      setActionLoading(prev => {
        const newState = { ...prev };
        delete newState[resumeId];
        return newState;
      });
    }
  };

  const handleRefresh = () => {
    fetchResumes(false);
  };

  const toggleSort = () => {
    setSortDirection(prev => prev === "asc" ? "desc" : "asc");
  };

  // Get unique domains for filter
  const uniqueDomains = Array.from(new Set(
    resumes.map(r => r.classified_domain).filter(Boolean)
  ));

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return 'Invalid date';
    }
  };

  if (loading) {
    return (
      <main className="flex flex-col min-h-screen bg-gray-900 text-white">
        <header className="flex flex-col items-center justify-center py-14 lg:py-24 text-center gap-4">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-tight bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            Your Resumes
          </h1>
        </header>
        <section className="flex-1 px-4 sm:px-10 pb-24">
          <div className="flex justify-center items-center h-64">
            <Loader2 className="h-16 w-16 animate-spin text-primary" />
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="flex flex-col min-h-screen bg-gray-900 text-white">
      <header className="flex flex-col items-center justify-center py-14 lg:py-24 text-center gap-4">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-tight bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
          Your Resumes
        </h1>
        <p className="max-w-2xl text-lg sm:text-xl text-muted-foreground">
          Manage your uploaded resumes or upload a new one.
        </p>
      </header>
      
      <section className="flex-1 px-4 sm:px-10 pb-24">
        <div className="max-w-6xl mx-auto">
          {error ? (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>{error}</span>
                <Button variant="outline" size="sm" onClick={() => fetchResumes()}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          ) : null}

          {/* Controls */}
          <div className="flex flex-col sm:flex-row gap-4 mb-8">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search resumes..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 bg-gray-800 border-gray-600"
                />
              </div>
            </div>
            
            <div className="flex gap-2">
              <Select value={selectedDomain} onValueChange={setSelectedDomain}>
                <SelectTrigger className="w-[150px] bg-gray-800 border-gray-600">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-gray-600">
                  <SelectItem value="all">All Domains</SelectItem>
                  {uniqueDomains.map(domain => (
                    <SelectItem key={domain} value={domain}>
                      {domain}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={sortBy} onValueChange={(value: SortOption) => setSortBy(value)}>
                <SelectTrigger className="w-[120px] bg-gray-800 border-gray-600">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-gray-600">
                  <SelectItem value="name">Name</SelectItem>
                  <SelectItem value="date">Date</SelectItem>
                  <SelectItem value="domain">Domain</SelectItem>
                </SelectContent>
              </Select>

              <Button variant="outline" size="icon" onClick={toggleSort} className="border-gray-600">
                {sortDirection === "asc" ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />}
              </Button>

              <Button variant="outline" size="icon" onClick={handleRefresh} className="border-gray-600">
                <RefreshCw className="h-4 w-4" />
              </Button>

              <Button onClick={() => router.push('/dashboard')} className="bg-primary hover:bg-primary/80">
                <PlusCircle className="mr-2 h-4 w-4" />
                Upload New
              </Button>
            </div>
          </div>

          {/* Results info */}
          <div className="text-sm text-muted-foreground mb-4">
            Showing {filteredResumes.length} of {resumes.length} resumes
          </div>

          {/* Content */}
          {resumes.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-medium mb-2">No resumes yet</h3>
              <p className="text-muted-foreground mb-6">
                Upload your first resume to get started with analysis.
              </p>
              <Button onClick={() => router.push('/dashboard')} className="bg-primary hover:bg-primary/80">
                <PlusCircle className="mr-2 h-4 w-4" />
                Upload Your First Resume
              </Button>
            </div>
          ) : filteredResumes.length === 0 ? (
            <div className="text-center py-12">
              <Search className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-medium mb-2">No resumes found</h3>
              <p className="text-muted-foreground">
                Try adjusting your search or filter criteria.
              </p>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {filteredResumes.map((resume) => (
                <Card key={resume.resume_id} className="bg-gray-800 border-gray-700 hover:border-gray-600 transition-colors">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-start gap-2 text-lg">
                      <FileText className="h-5 w-5 text-accent flex-shrink-0 mt-0.5" />
                      <span className="truncate" title={resume.filename}>
                        {resume.filename}
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="space-y-3 mb-4">
                      <div className="text-sm text-muted-foreground flex items-center gap-2">
                        <Calendar className="h-4 w-4" />
                        <span>{formatDate(resume.created_at)}</span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Domain:</span>
                        {resume.classified_domain ? (
                          <Badge variant="secondary" className="text-xs">
                            {resume.classified_domain}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground italic">
                            Not classified
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => handleView(resume.resume_id)} 
                        className="flex-1 border-gray-600 hover:bg-gray-700"
                        disabled={actionLoading[resume.resume_id] === "deleting"}
                      >
                        <Eye className="mr-1 h-4 w-4" /> 
                        View
                      </Button>
                      
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => handleDownload(resume.resume_id)} 
                        className="flex-1 border-gray-600 hover:bg-gray-700"
                        disabled={!!actionLoading[resume.resume_id]}
                      >
                        {actionLoading[resume.resume_id] === "downloading" ? (
                          <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                        ) : (
                          <Download className="mr-1 h-4 w-4" />
                        )}
                        Download
                      </Button>
                      
                      <Button 
                        variant="destructive" 
                        size="sm" 
                        onClick={() => handleDelete(resume.resume_id)}
                        disabled={!!actionLoading[resume.resume_id]}
                        className="px-3"
                      >
                        {actionLoading[resume.resume_id] === "deleting" ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
};

export default ResumesPage;
