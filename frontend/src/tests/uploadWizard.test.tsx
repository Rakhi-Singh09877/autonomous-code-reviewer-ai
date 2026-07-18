/**
 * src/tests/uploadWizard.test.tsx
 *
 * Phase 3 unit tests for UploadWizard component and form validation.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { UploadWizard } from "../features/analysis/components/UploadWizard";

describe("UploadWizard Component & Zod Validation Tests", () => {
  let successMock = vi.fn();

  beforeEach(() => {
    successMock = vi.fn();
  });

  it("should render default Git tab and related input fields", () => {
    render(<UploadWizard onSuccess={successMock} />);
    
    expect(screen.getByRole("tab", { name: /git repository/i })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /zip archive upload/i })).toBeTruthy();
    
    expect(screen.getByLabelText(/git repository url/i)).toBeTruthy();
    expect(screen.getByLabelText(/branch/i)).toBeTruthy();
    expect(screen.getByLabelText(/focus areas/i)).toBeTruthy();
    expect(screen.getByLabelText(/max issues per file/i)).toBeTruthy();
  });

  it("should validate and display error on empty Git URL submission", () => {
    render(<UploadWizard onSuccess={successMock} />);
    
    const submitBtn = screen.getByRole("button", { name: /start analysis/i });
    fireEvent.click(submitBtn);
    
    expect(screen.getByText(/must be a valid git url/i)).toBeTruthy();
    expect(successMock).not.toHaveBeenCalled();
  });

  it("should validate and display error on invalid Git URL format", () => {
    render(<UploadWizard onSuccess={successMock} />);
    
    const gitInput = screen.getByLabelText(/git repository url/i);
    fireEvent.change(gitInput, { target: { value: "invalid-url-format" } });
    
    const submitBtn = screen.getByRole("button", { name: /start analysis/i });
    fireEvent.click(submitBtn);
    
    expect(screen.getByText(/must be a valid git url/i)).toBeTruthy();
    expect(successMock).not.toHaveBeenCalled();
  });

  it("should validate and display error on negative max issues per file", () => {
    render(<UploadWizard onSuccess={successMock} />);
    
    const gitInput = screen.getByLabelText(/git repository url/i);
    fireEvent.change(gitInput, { target: { value: "https://github.com/test/repo" } });
    
    const maxIssuesInput = screen.getByLabelText(/max issues per file/i);
    fireEvent.change(maxIssuesInput, { target: { value: "-5" } });
    
    const submitBtn = screen.getByRole("button", { name: /start analysis/i });
    fireEvent.click(submitBtn);
    
    expect(screen.getByText(/must be a positive integer/i)).toBeTruthy();
    expect(successMock).not.toHaveBeenCalled();
  });

  it("should switch tabs and show ZIP upload drag zone", () => {
    render(<UploadWizard onSuccess={successMock} />);
    
    const zipTab = screen.getByRole("tab", { name: /zip archive upload/i });
    fireEvent.click(zipTab);
    
    expect(screen.getByText(/drag & drop your zip file, or browse/i)).toBeTruthy();
    expect(screen.queryByLabelText(/git repository url/i)).toBeNull();
  });

  it("should display validation error if ZIP file is not selected", () => {
    render(<UploadWizard onSuccess={successMock} />);
    
    const zipTab = screen.getByRole("tab", { name: /zip archive upload/i });
    fireEvent.click(zipTab);
    
    const submitBtn = screen.getByRole("button", { name: /start analysis/i });
    fireEvent.click(submitBtn);
    
    expect(screen.getByText(/zip file is required/i)).toBeTruthy();
    expect(successMock).not.toHaveBeenCalled();
  });

  it("should trigger onSuccess on successful Git configuration submission", () => {
    render(<UploadWizard onSuccess={successMock} />);
    
    const gitInput = screen.getByLabelText(/git repository url/i);
    fireEvent.change(gitInput, { target: { value: "https://github.com/user/test-project" } });
    
    const branchInput = screen.getByLabelText(/branch/i);
    fireEvent.change(branchInput, { target: { value: "development" } });
    
    const focusInput = screen.getByLabelText(/focus areas/i);
    fireEvent.change(focusInput, { target: { value: "security, performance" } });

    const submitBtn = screen.getByRole("button", { name: /start analysis/i });
    fireEvent.click(submitBtn);
    
    expect(successMock).toHaveBeenCalledTimes(1);
    expect(successMock).toHaveBeenCalledWith({
      method: "git",
      payload: {
        gitUrl: "https://github.com/user/test-project",
        branch: "development",
        focusAreas: ["security", "performance"],
        maxIssuesPerFile: 10,
      },
    });
  });

  it("should clear form fields on clicking Reset button", () => {
    render(<UploadWizard onSuccess={successMock} />);
    
    const gitInput = screen.getByLabelText(/git repository url/i);
    fireEvent.change(gitInput, { target: { value: "https://github.com/user/project" } });
    
    const resetBtn = screen.getByRole("button", { name: /reset/i });
    fireEvent.click(resetBtn);
    
    expect((gitInput as HTMLInputElement).value).toBe("");
  });
});
