import { useState, useEffect } from "react";
import {
  FileText,
  Image,
  FileQuestion,
  Download,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { convertPdfToImage } from "@/lib/pdf2img";
import api from "@/lib/api";
import { toast } from "sonner";

export default function ResumePreviewSlider({
  resumeId,
  fileName,
}: {
  resumeId: string;
  fileName?: string;
}) {
  const isPdf = fileName?.toLowerCase().endsWith(".pdf");
  const downloadUrl = resumeId
    ? `${api.defaults.baseURL}/api/v1/projects/resume/${resumeId}/download`
    : "";

  const [imageUrls, setImageUrls] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Cleanup function to revoke object URLs and prevent memory leaks
    return () => {
      imageUrls.forEach(URL.revokeObjectURL);
    };
  }, [imageUrls]);

  useEffect(() => {
    if (!isPdf || !downloadUrl || !resumeId) {
      setIsLoading(false);
      return;
    }

    const fetchAndConvertPdf = async () => {
      setIsLoading(true);
      setError(null);
      setImageUrls([]);
      setCurrentPage(0);

      try {
        console.log("Fetching PDF from:", downloadUrl);

        // 1. Fetch the PDF as a blob from your backend API
        const response = await api.get(downloadUrl, {
          responseType: "blob",
          headers: {
            Accept: "application/pdf, application/octet-stream",
          },
        });

        console.log("PDF fetched successfully, size:", response.data.size);

        // 2. Create a File object from the blob
        const pdfFile = new File([response.data], fileName || "resume.pdf", {
          type: "application/pdf",
        });

        console.log("Created PDF file object:", pdfFile.name, pdfFile.size);

        // 3. Convert the PDF file to images using your existing converter
        const result = await convertPdfToImage(pdfFile);

        console.log("Conversion result:", result);

        if (result.error) {
          setError(result.error);
        } else if (result.imageUrls && result.imageUrls.length > 0) {
          setImageUrls(result.imageUrls);
          console.log(
            `Successfully converted ${result.imageUrls.length} pages to images`
          );
        } else {
          setError("Could not generate a preview for this PDF.");
        }
      } catch (err) {
        console.error("Failed to fetch or convert PDF:", err);

        // More specific error handling with type guard
        if (typeof err === "object" && err !== null) {
          const anyErr = err as any;
          if (anyErr.response?.status === 404) {
            setError(
              "Resume not found or you don't have permission to view it."
            );
          } else if (anyErr.response?.status === 401) {
            setError("You need to be logged in to view this resume.");
          } else if (anyErr.response?.status >= 500) {
            setError(
              "Server error while loading the resume. Please try again later."
            );
          } else if (
            typeof anyErr.message === "string" &&
            anyErr.message.includes("Network Error")
          ) {
            setError(
              "Network error. Please check your connection and try again."
            );
          } else {
            setError("An error occurred while loading the resume preview.");
          }
        } else {
          setError("An error occurred while loading the resume preview.");
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchAndConvertPdf();
  }, [resumeId, fileName, downloadUrl, isPdf]);

  const getFileIcon = (filename: string = "") => {
    const ext = filename.split(".").pop()?.toLowerCase() || "";
    if (ext === "pdf") return <FileText className="w-12 h-12 text-red-500" />;
    if (["jpg", "jpeg", "png", "gif"].includes(ext))
      return <Image className="w-12 h-12 text-blue-500" />;
    return <FileQuestion className="w-12 h-12 text-gray-500" />;
  };

  const getFileType = (filename: string = "") => {
    const ext = filename.split(".").pop()?.toLowerCase() || "";
    if (ext === "pdf") return "PDF Document";
    if (["jpg", "jpeg", "png", "gif"].includes(ext)) return "Image File";
    if (["doc", "docx"].includes(ext)) return "Word Document";
    return "Document File";
  };

  const handlePrevPage = () => {
    setCurrentPage((prev) => Math.max(prev - 1, 0));
  };

  const handleNextPage = () => {
    setCurrentPage((prev) => Math.min(prev + 1, imageUrls.length - 1));
  };

  const handleDownload = () => {
    if (!downloadUrl) return;
    try {
      // Create a temporary anchor element to trigger the download
      const link = document.createElement("a");
      link.href = downloadUrl;
      // Set the download attribute to suggest a filename to the browser
      link.setAttribute("download", fileName || "download");

      // Append the link to the body, trigger the click, and then remove it
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error: any) {
      console.error("Failed to download resume:", error);
      const errorMessage =
        error.response?.data?.message || "Failed to download resume";
      toast.error(errorMessage);
    }
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="aspect-[8.5/11] flex flex-col items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg p-6">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
          <p className="mt-4 text-sm text-gray-600 dark:text-gray-400">
            Generating Preview...
          </p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="aspect-[8.5/11] flex flex-col items-center justify-center bg-red-50 dark:bg-red-900/20 rounded-lg p-6 text-center">
          <FileQuestion className="w-12 h-12 text-red-500 mb-4" />
          <h3 className="text-lg font-medium text-red-700 dark:text-red-300 mb-2">
            Preview Failed
          </h3>
          <p className="text-sm text-red-600 dark:text-red-400 mb-4">{error}</p>
          <Button
            onClick={handleDownload}
            disabled={!downloadUrl}
            className="mb-2"
          >
            <Download className="mr-2 h-4 w-4" />
            Download Original
          </Button>
        </div>
      );
    }

    if (isPdf && imageUrls.length > 0) {
      return (
        <div className="relative group bg-white rounded-lg overflow-hidden">
          {/* Main image display */}
          <img
            src={imageUrls[currentPage]}
            alt={`Resume Page ${currentPage + 1}`}
            className="w-full aspect-[8.5/11] object-contain bg-white"
            style={{ maxHeight: "800px" }}
          />

          {/* Navigation controls - only show if multiple pages */}
          {imageUrls.length > 1 && (
            <>
              {/* Previous page button */}
              <div className="absolute top-0 left-0 bottom-0 flex items-center">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handlePrevPage}
                  disabled={currentPage === 0}
                  className="m-2 bg-black/20 text-white hover:bg-black/50 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-6 w-6" />
                </Button>
              </div>

              {/* Next page button */}
              <div className="absolute top-0 right-0 bottom-0 flex items-center">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleNextPage}
                  disabled={currentPage === imageUrls.length - 1}
                  className="m-2 bg-black/20 text-white hover:bg-black/50 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-6 w-6" />
                </Button>
              </div>

              {/* Page indicator */}
              <div className="absolute bottom-2 left-1/2 -translate-x-1/2 bg-black/50 text-white text-xs font-semibold px-2 py-1 rounded-full">
                {currentPage + 1} / {imageUrls.length}
              </div>

              {/* Page dots navigation for easy access */}
              {imageUrls.length <= 10 && (
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex gap-1">
                  {imageUrls.map((_, index) => (
                    <button
                      key={index}
                      onClick={() => setCurrentPage(index)}
                      className={`w-2 h-2 rounded-full transition-colors ${
                        index === currentPage ? "bg-white" : "bg-white/50"
                      }`}
                      aria-label={`Go to page ${index + 1}`}
                    />
                  ))}
                </div>
              )}
            </>
          )}

          {/* Download button overlay */}
          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleDownload}
              className="bg-black/20 text-white hover:bg-black/50 hover:text-white"
              title="Download PDF"
            >
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>
      );
    }

    // Fallback for non-PDFs or other cases
    return (
      <div className="aspect-[8.5/11] flex flex-col items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg p-6">
        <div className="mb-4">{getFileIcon(fileName)}</div>
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">
            {fileName || "Resume Preview"}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
            {getFileType(fileName)}
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mb-4">
            Live preview is not available for this file type.
          </p>
          <Button onClick={handleDownload} disabled={!downloadUrl}>
            <Download className="mr-2 h-4 w-4" />
            Download
          </Button>
        </div>
      </div>
    );
  };

  return (
    <div className="lg:col-span-1">
      <div className="rounded-2xl shadow-sm overflow-hidden bg-gray-200 dark:bg-gray-900">
        {renderContent()}
      </div>

      {/* File info footer */}
      {fileName && !error && imageUrls.length > 0 && (
        <div className="mt-2 text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {fileName} • {imageUrls.length} page
            {imageUrls.length !== 1 ? "s" : ""}
          </p>
        </div>
      )}
    </div>
  );
}
