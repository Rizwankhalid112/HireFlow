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
        <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
          <div className="max-w-md text-center">
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
              Something went wrong
            </h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
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
