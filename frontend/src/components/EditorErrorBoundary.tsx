import { Component, type ErrorInfo, type ReactNode } from "react";

interface EditorErrorBoundaryProps {
  children: ReactNode;
  fallback: ReactNode;
}

interface EditorErrorBoundaryState {
  failed: boolean;
}

export class EditorErrorBoundary extends Component<
  EditorErrorBoundaryProps,
  EditorErrorBoundaryState
> {
  state: EditorErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): EditorErrorBoundaryState {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Markdown editor failed to load", error, info);
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
