import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router-dom";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled app error", error, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-6 text-center">
        <p className="text-xs uppercase tracking-widest text-slate-500">Error</p>
        <h2 className="mt-2 text-xl font-bold text-slate-100">表示中に問題が発生しました</h2>
        <p className="mt-2 text-sm text-slate-400">
          ページを再読み込みするか、主要ページへ戻ってください。
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-3">
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
          >
            再読み込み
          </button>
          <Link to="/" className="rounded-md border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-700">
            トップへ戻る
          </Link>
          <Link to="/tournament" className="rounded-md border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-700">
            大会モード
          </Link>
        </div>
      </div>
    );
  }
}

