import { useCallback, useEffect, useRef, useState } from 'react'

const FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  'a[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

export function useRemote(loader, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const reload = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    if (!silent) setError('')
    try {
      setData(await loader())
    } catch (caught) {
      if (!silent) setError(caught.message)
    } finally {
      if (!silent) setLoading(false)
    }
  }, deps)

  useEffect(() => {
    reload()
  }, [reload])

  return { data, loading, error, reload, setData }
}

export function useDialogFocus({ active = true, onClose } = {}) {
  const dialogRef = useRef(null)
  const closeRef = useRef(onClose)
  closeRef.current = onClose

  useEffect(() => {
    if (!active) return undefined
    const dialog = dialogRef.current
    if (!dialog) return undefined

    const previouslyFocused = document.activeElement
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const getFocusable = () => Array.from(dialog.querySelectorAll(FOCUSABLE_SELECTOR))
      .filter((element) => !element.hasAttribute('hidden') && element.getAttribute('aria-hidden') !== 'true')

    const focusFrame = window.requestAnimationFrame(() => {
      const target = dialog.querySelector('[autofocus]') || getFocusable()[0] || dialog
      target.focus?.({ preventScroll: true })
    })
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && closeRef.current) {
        event.preventDefault()
        closeRef.current()
        return
      }
      if (event.key !== 'Tab') return
      const focusable = getFocusable()
      if (!focusable.length) {
        event.preventDefault()
        dialog.focus()
        return
      }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      window.cancelAnimationFrame(focusFrame)
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
      previouslyFocused?.focus?.({ preventScroll: true })
    }
  }, [active])

  return dialogRef
}
