import { useEffect, useRef } from 'react'

const FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  'a[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

// Several dialog surfaces can overlap briefly during a hand-off. Keep one
// shared lock so closing an older surface cannot re-enable page scrolling
// while the newer dialog is still open.
let scrollLockCount = 0
let bodyOverflowBeforeDialogLock = ''

const lockBodyScroll = () => {
  if (scrollLockCount === 0) {
    bodyOverflowBeforeDialogLock = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  }
  scrollLockCount += 1

  let released = false
  return () => {
    if (released) return
    released = true
    scrollLockCount = Math.max(0, scrollLockCount - 1)
    if (scrollLockCount === 0) {
      document.body.style.overflow = bodyOverflowBeforeDialogLock
      bodyOverflowBeforeDialogLock = ''
    }
  }
}

/**
 * Keeps keyboard focus inside an open dialog and restores it when the dialog closes.
 * It also locks the page behind the sheet so mobile Safari does not scroll two layers.
 */
export function useDialogFocus({ active = true, onClose } = {}) {
  const dialogRef = useRef(null)
  const closeRef = useRef(onClose)
  closeRef.current = onClose

  useEffect(() => {
    if (!active) return undefined

    const dialog = dialogRef.current
    if (!dialog) return undefined

    const previouslyFocused = document.activeElement
    const releaseBodyScroll = lockBodyScroll()

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
      releaseBodyScroll()
      previouslyFocused?.focus?.({ preventScroll: true })
    }
  }, [active])

  return dialogRef
}
