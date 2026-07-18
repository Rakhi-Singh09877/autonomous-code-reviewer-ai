"use client";

import React, { useState, useRef } from "react";
import { uploadSubmissionSchema } from "../validation/uploadSchema";

export interface ValidatedUploadPayload {
  method: "git" | "zip";
  payload: {
    gitUrl?: string;
    branch?: string;
    zipFile?: File;
    focusAreas: string[];
    maxIssuesPerFile: number;
  };
}

interface UploadWizardProps {
  onSuccess?: (data: ValidatedUploadPayload) => void;
}

export const UploadWizard: React.FC<UploadWizardProps> = ({ onSuccess }) => {
  const [activeTab, setActiveTab] = useState<"git" | "zip">("git");
  
  // Form fields
  const [gitUrl, setGitUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [focusAreas, setFocusAreas] = useState("");
  const [maxIssuesPerFile, setMaxIssuesPerFile] = useState("10");

  // Validation errors
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Drag and drop handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setZipFile(file);
      setErrors((prev) => ({ ...prev, zipFile: "" }));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setZipFile(e.target.files[0]);
      setErrors((prev) => ({ ...prev, zipFile: "" }));
    }
  };

  const clearForm = () => {
    setGitUrl("");
    setBranch("");
    setZipFile(null);
    setFocusAreas("");
    setMaxIssuesPerFile("10");
    setErrors({});
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    const rawPayload = {
      gitUrl: activeTab === "git" ? gitUrl : undefined,
      branch: activeTab === "git" ? (branch || undefined) : undefined,
      zipFile: activeTab === "zip" ? (zipFile || undefined) : undefined,
      focusAreas: focusAreas || undefined,
      maxIssuesPerFile: maxIssuesPerFile,
    };

    const result = uploadSubmissionSchema.safeParse(rawPayload);

    if (!result.success) {
      const formattedErrors: Record<string, string> = {};
      result.error.issues.forEach((err) => {
        if (err.path[0]) {
          formattedErrors[err.path[0].toString()] = err.message;
        }
      });
      setErrors(formattedErrors);
      return;
    }

    if (onSuccess) {
      const focusAreasArray = focusAreas
        ? focusAreas.split(",").map((s) => s.trim()).filter((s) => s.length > 0)
        : [];

      onSuccess({
        method: activeTab,
        payload: {
          gitUrl: activeTab === "git" ? result.data.gitUrl || undefined : undefined,
          branch: activeTab === "git" ? result.data.branch || undefined : undefined,
          zipFile: activeTab === "zip" ? result.data.zipFile || undefined : undefined,
          focusAreas: focusAreasArray,
          maxIssuesPerFile: result.data.maxIssuesPerFile,
        },
      });
    }
  };


  return (
    <div className="w-full max-w-xl mx-auto rounded-xl border border-zinc-800 bg-zinc-950 p-6 text-zinc-100 shadow-xl transition-all duration-300 hover:border-zinc-700">
      <div className="mb-6">
        <h2 className="text-xl font-bold tracking-tight text-white mb-2">
          New Analysis Wizard
        </h2>
        <p className="text-sm text-zinc-400">
          Choose a repository integration method to start real-time review.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-zinc-800 mb-6" role="tablist">
        <button
          type="button"
          onClick={() => {
            setActiveTab("git");
            setErrors({});
          }}
          className={`flex-1 pb-3 text-sm font-medium transition-colors duration-200 border-b-2 outline-none focus:text-cyan-400 ${
            activeTab === "git"
              ? "border-cyan-500 text-cyan-400"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
          role="tab"
          aria-selected={activeTab === "git"}
          aria-controls="git-tab-content"
          id="git-tab"
        >
          Git Repository
        </button>
        <button
          type="button"
          onClick={() => {
            setActiveTab("zip");
            setErrors({});
          }}
          className={`flex-1 pb-3 text-sm font-medium transition-colors duration-200 border-b-2 outline-none focus:text-cyan-400 ${
            activeTab === "zip"
              ? "border-cyan-500 text-cyan-400"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
          role="tab"
          aria-selected={activeTab === "zip"}
          aria-controls="zip-tab-content"
          id="zip-tab"
        >
          ZIP Archive Upload
        </button>
      </div>

      <form onSubmit={handleSubmit} noValidate>
        {/* Form Inputs based on active tab */}
        {activeTab === "git" ? (
          <div id="git-tab-content" role="tabpanel" aria-labelledby="git-tab" className="space-y-4">
            <div>
              <label htmlFor="gitUrl" className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                Git Repository URL <span className="text-cyan-500">*</span>
              </label>
              <input
                id="gitUrl"
                type="url"
                placeholder="https://github.com/username/repository"
                value={gitUrl}
                onChange={(e) => setGitUrl(e.target.value)}
                className={`w-full rounded-md border bg-zinc-900 px-3.5 py-2 text-sm text-white placeholder-zinc-500 outline-none transition duration-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/20 ${
                  errors.gitUrl ? "border-red-500" : "border-zinc-800"
                }`}
              />
              {errors.gitUrl && (
                <p className="mt-1.5 text-xs text-red-400 font-medium">{errors.gitUrl}</p>
              )}
            </div>

            <div>
              <label htmlFor="branch" className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                Branch (Optional)
              </label>
              <input
                id="branch"
                type="text"
                placeholder="main"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-3.5 py-2 text-sm text-white placeholder-zinc-500 outline-none transition duration-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/20"
              />
            </div>
          </div>
        ) : (
          <div id="zip-tab-content" role="tabpanel" aria-labelledby="zip-tab" className="space-y-4">
            <div>
              <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                ZIP Archive <span className="text-cyan-500">*</span>
              </span>
              
              <div
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-6 cursor-pointer transition-all duration-200 bg-zinc-900/50 hover:bg-zinc-900 ${
                  dragActive ? "border-cyan-500 bg-zinc-900" : "border-zinc-800 hover:border-zinc-700"
                } ${errors.zipFile ? "border-red-500" : ""}`}
              >
                <input
                  ref={fileInputRef}
                  id="zipFileInput"
                  type="file"
                  accept=".zip"
                  onChange={handleFileChange}
                  className="hidden"
                />
                
                <svg className="w-8 h-8 text-zinc-500 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>

                <p className="text-sm font-medium text-zinc-300 text-center">
                  {zipFile ? zipFile.name : "Drag & drop your ZIP file, or browse"}
                </p>
                <p className="text-xs text-zinc-500 mt-1">
                  {zipFile ? `${(zipFile.size / 1024 / 1024).toFixed(2)} MB` : "Only .zip file extensions are allowed"}
                </p>
              </div>

              {errors.zipFile && (
                <p className="mt-1.5 text-xs text-red-400 font-medium">{errors.zipFile}</p>
              )}
            </div>
          </div>
        )}

        {/* Common Configuration Inputs */}
        <div className="mt-6 pt-6 border-t border-zinc-900 space-y-4">
          <div>
            <label htmlFor="focusAreas" className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
              Focus Areas (Optional)
            </label>
            <input
              id="focusAreas"
              type="text"
              placeholder="e.g. security, performance, clean-code"
              value={focusAreas}
              onChange={(e) => setFocusAreas(e.target.value)}
              className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-3.5 py-2 text-sm text-white placeholder-zinc-500 outline-none transition duration-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/20"
            />
          </div>

          <div>
            <label htmlFor="maxIssuesPerFile" className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
              Max Issues Per File
            </label>
            <input
              id="maxIssuesPerFile"
              type="number"
              min="1"
              value={maxIssuesPerFile}
              onChange={(e) => setMaxIssuesPerFile(e.target.value)}
              className={`w-full rounded-md border bg-zinc-900 px-3.5 py-2 text-sm text-white outline-none transition duration-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/20 ${
                errors.maxIssuesPerFile ? "border-red-500" : "border-zinc-800"
              }`}
            />
            {errors.maxIssuesPerFile && (
              <p className="mt-1.5 text-xs text-red-400 font-medium">{errors.maxIssuesPerFile}</p>
            )}
          </div>
        </div>

        {/* Form Action Controls */}
        <div className="mt-8 flex justify-end gap-3.5">
          <button
            type="button"
            onClick={clearForm}
            className="rounded-md border border-zinc-800 px-4.5 py-2 text-sm font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50 transition duration-200"
          >
            Reset
          </button>
          
          <button
            type="submit"
            className="rounded-md bg-cyan-500 px-5.5 py-2 text-sm font-semibold text-zinc-950 hover:bg-cyan-400 shadow-md shadow-cyan-500/10 hover:shadow-cyan-500/20 transition duration-200"
          >
            Start Analysis
          </button>
        </div>
      </form>
    </div>
  );
};

export default UploadWizard;
