import { Component } from 'react';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-surface-2 px-4">
          <div className="max-w-md text-center">
            <h1 className="text-2xl font-semibold text-ink">
              Something went wrong
            </h1>
            <p className="mt-2 text-sm text-muted">
              An unexpected error occurred. Please refresh the page or return home.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <Button onClick={() => window.location.reload()}>Refresh</Button>
              <Link to="/">
                <Button variant="secondary">Go home</Button>
              </Link>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
