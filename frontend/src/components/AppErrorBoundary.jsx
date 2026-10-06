/**
 * components/AppErrorBoundary.jsx — Lưới an toàn cuối cùng khi React render lỗi.
 *
 * Bọc quanh toàn bộ ứng dụng trong main.jsx. Khi bất kỳ component nào ném lỗi lúc render,
 * thay vì để trang trắng trơn, file này hiện màn "Frontend gặp lỗi khi render" kèm nội dung
 * lỗi và nút "Tải lại trang". Chi tiết đầy đủ được in ra Console của trình duyệt.
 *
 * Phân biệt với BackendGate trong App.jsx: chỗ kia là lỗi BACKEND, chỗ này là lỗi CODE GIAO DIỆN.
 * Đây là class component (không phải hàm) vì React chỉ hỗ trợ error boundary theo dạng class.
 */
import { Component } from 'react'

export class AppErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Application render failed', error, info)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <main className="backend-gate backend-gate--error">
        <div>
          <span>Không thể hiển thị giao diện</span>
          <h1>Frontend gặp lỗi khi render.</h1>
          <p>{this.state.error.message || 'Lỗi không xác định.'}</p>
          <button type="button" onClick={() => window.location.reload()}>Tải lại trang</button>
        </div>
      </main>
    )
  }
}
