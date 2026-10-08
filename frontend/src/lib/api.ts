import axios from "axios";

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_BASE_URL;

if (process.env.NODE_ENV === 'production' && !backendUrl) {
  console.error("FATAL: NEXT_PUBLIC_BACKEND_BASE_URL is not set in production environment.");
}

const api = axios.create({
  baseURL: backendUrl || 'http://localhost:8000',
  withCredentials: true,
  headers: {
    'ngrok-skip-browser-warning': 'true',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:; frame-ancestors 'none';"
  },
  timeout: 300000, // 30 second timeout
});

// Request interceptor to add security headers
api.interceptors.request.use(
  (config) => {
    // Add CSRF protection if needed
    // config.headers['X-CSRF-Token'] = getCSRFToken();
    
    // Prevent CRLF injection
    if (config.headers) {
      Object.keys(config.headers).forEach(key => {
        const value = config.headers[key];
        if (typeof value === 'string') {
          // Remove potential CRLF injection
          config.headers[key] = value.replace(/[\\r\\n]/g, '');
        }
      });
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);


// Enhanced upload function with progress tracking
api.uploadWithProgress = (url: string, formData: FormData, onUploadProgress?: (progress: number) => void) => {
  return api.post(url, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent: any) => {
      if (onUploadProgress && progressEvent.total) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onUploadProgress(percentCompleted);
      }
    }
  });
};

// SSE upload method for streaming responses - Updated to work with httpOnly cookies
api.uploadWithSSE = async (
  url: string, 
  formData: FormData, 
  onProgress?: (progress: number) => void, 
  onMessage?: (data: any) => void
) => {
  const baseURL = backendUrl || 'http://localhost:8000';
  
  console.log("Making SSE request to:", `${baseURL}${url}`);

  // Use fetch with credentials: 'include' to send httpOnly cookies automatically
  const response = await fetch(`${baseURL}${url}`, {
    method: 'POST',
    body: formData,
    headers: {
      'ngrok-skip-browser-warning': 'true'
      // Don't manually set Authorization header - let cookies handle authentication
    },
    credentials: 'include' // This sends httpOnly cookies automatically
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error("Response error:", response.status, errorText);
    throw new Error(`Server responded with ${response.status}: ${response.statusText}. ${errorText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Failed to read response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const jsonStr = line.substring(6);
        try {
          const data = JSON.parse(jsonStr);
          if (onMessage) {
            onMessage(data);
          }
        } catch (e) {
          console.warn("Failed to parse SSE data:", jsonStr, e);
        }
      }
    }
  }
};

// Alternative: Use axios for upload with streaming response
api.uploadWithAxiosSSE = async (
  url: string,
  formData: FormData,
  onProgress?: (progress: number) => void,
  onMessage?: (data: any) => void
) => {
  try {
    const response = await api.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'stream',
      onUploadProgress: (progressEvent: any) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percentCompleted);
        }
      }
    });

    // Handle streaming response
    const reader = response.data.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const jsonStr = line.substring(6);
          try {
            const data = JSON.parse(jsonStr);
            if (onMessage) {
              onMessage(data);
            }
          } catch (e) {
            console.warn("Failed to parse SSE data:", jsonStr, e);
          }
        }
      }
    }
  } catch (error: any) {
    console.error("Axios SSE upload error:", error);
    throw error;
  }
};

// Server-Sent Events helper - Updated for httpOnly cookies
api.createSSEConnection = (url: string, options: any = {}) => {
  const baseURL = backendUrl || 'http://localhost:8000';
  
  return new EventSource(`${baseURL}${url}`, {
    withCredentials: true, // This sends cookies automatically
    ...options
  });
};

// Download resume file
// api.downloadResume = async (resumeId: string): Promise<Blob> => {
//   const baseURL = backendUrl || 'http://localhost:8000';
//   const response = await fetch(`${baseURL}/api/v1/projects/resume/${resumeId}/download`, {
//     method: 'GET',
//     credentials: 'include' // Send cookies with the request
//   });

//   if (!response.ok) {
//     throw new Error(`Failed to download resume: ${response.status} ${response.statusText}`);
//   }

//   return await response.blob();
// };

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Handle network errors
    if (!error.response) {
      console.error("Network error:", error.message);
      return Promise.reject(new Error("Network connection failed. Please check your internet connection."));
    }
    
    // Handle 401 Unauthorized
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        await api.post(`/api/v1/auth/refresh`);
        return api(originalRequest);
      } catch (refreshError) {
        // Redirect to login page
        if (typeof window !== 'undefined') {
          window.location.href = "/sign-in";
        }
        return Promise.reject(new Error("Session expired. Please log in again."));
      }
    }
    
    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      return Promise.reject(new Error("Access denied. You don't have permission to perform this action."));
    }
    
    // Handle 404 Not Found
    if (error.response?.status === 404) {
      return Promise.reject(new Error("Resource not found."));
    }
    
    // Handle 500 Internal Server Error
    if (error.response?.status === 500) {
      return Promise.reject(new Error("Server error. Please try again later."));
    }
    
    // Handle rate limiting
    if (error.response?.status === 429) {
      return Promise.reject(new Error("Too many requests. Please try again later."));
    }
    
    // Handle validation errors
    if (error.response?.status === 422) {
      const errorMessage = error.response.data?.message || "Validation error occurred.";
      return Promise.reject(new Error(errorMessage));
    }
    
    // Handle generic errors
    const errorMessage = error.response.data?.message || error.message || "An unexpected error occurred.";
    return Promise.reject(new Error(errorMessage));
  }
);

// Extend the axios instance type to include our custom methods
declare module 'axios' {
  interface AxiosInstance {
    uploadWithProgress: (url: string, formData: FormData, onUploadProgress?: (progress: number) => void) => Promise<any>;
    uploadWithSSE: (url: string, formData: FormData, onProgress?: (progress: number) => void, onMessage?: (data: any) => void) => Promise<void>;
    uploadWithAxiosSSE: (url: string, formData: FormData, onProgress?: (progress: number) => void, onMessage?: (data: any) => void) => Promise<void>;
    createSSEConnection: (url: string, options?: any) => EventSource;
    downloadResume: (resumeId: string) => Promise<Blob>;
  }
}

export default api;
