export interface PdfConversionResult {
  imageUrls: string[]; // Now supports multiple images
  files: File[];       // Array of image files
  error?: string;
}

let pdfjsLib: any = null;
let isLoading = false;
let loadPromise: Promise<any> | null = null;

async function loadPdfJs(): Promise<any> {
    if (pdfjsLib) return pdfjsLib;
    if (loadPromise) return loadPromise;

    isLoading = true;
    // @ts-expect-error - pdfjs-dist/build/pdf.mjs is not a module
    loadPromise = import("pdfjs-dist/build/pdf.mjs").then((lib) => {
        // Set the worker source to use local file
        lib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
        pdfjsLib = lib;
        isLoading = false;
        return lib;
    });

    return loadPromise;
}

export async function convertPdfToImage(
  file: File
): Promise<PdfConversionResult> {
  try {
    const lib = await loadPdfJs();

    const arrayBuffer = await file.arrayBuffer();
    const pdf = await lib.getDocument({ data: arrayBuffer }).promise;

    const totalPages = pdf.numPages;

    if (totalPages > 2) {
      return {
        imageUrls: [],
        files: [],
        error: "Only up to 2 pages are supported",
      };
    }

    const imageUrls: string[] = [];
    const files: File[] = [];

    for (let pageNumber = 1; pageNumber <= totalPages; pageNumber++) {
      const page = await pdf.getPage(pageNumber);

      const viewport = page.getViewport({ scale: 4 });
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");

      canvas.width = viewport.width;
      canvas.height = viewport.height;

      if (context) {
        context.imageSmoothingEnabled = true;
        context.imageSmoothingQuality = "high";
      }

      await page.render({ canvasContext: context!, viewport }).promise;

      const blob: Blob | null = await new Promise((resolve) =>
        canvas.toBlob((b) => resolve(b), "image/png", 1.0)
      );

      if (blob) {
        const originalName = file.name.replace(/\.pdf$/i, "");
        const imageFile = new File([blob], `${originalName}-page${pageNumber}.png`, {
          type: "image/png",
        });

        const imageUrl = URL.createObjectURL(blob);

        imageUrls.push(imageUrl);
        files.push(imageFile);
      } else {
        return {
          imageUrls: [],
          files: [],
          error: `Failed to create image blob for page ${pageNumber}`,
        };
      }
    }

    return { imageUrls, files };
  } catch (err) {
    return {
      imageUrls: [],
      files: [],
      error: `Failed to convert PDF: ${err}`,
    };
  }
}