import { useEffect, useRef, type ReactNode } from "react";

interface ModalProps {
  /** Открыто ли модальное окно */
  open: boolean;
  /** Закрытие модального окна */
  onClose: () => void;
  /** Содержимое модального окна */
  children: ReactNode;
  /**
   * Закрывать по Enter (по умолчанию true).
   * Ставить false для модалок с формами/текстовыми полями.
   */
  closeOnEnter?: boolean;
  /** Дополнительный CSS-класс для контент-блока */
  className?: string;
}

/**
 * Универсальная обёртка модального окна.
 * - Escape → закрытие
 * - Enter → закрытие (если closeOnEnter не отключен)
 * - Клик по затемнённому фону → закрытие
 */
export function Modal({
  open,
  onClose,
  children,
  closeOnEnter = true,
  className,
}: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
      if (closeOnEnter && e.key === "Enter") {
        // Не закрываем если фокус в textarea или button
        const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
        if (tag === "textarea" || tag === "button") return;
        e.preventDefault();
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose, closeOnEnter]);

  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
    >
      <div
        className={
          className ||
          "relative bg-slate-900 border border-slate-700/60 rounded-2xl p-6 max-w-md w-full shadow-2xl shadow-sky-900/40"
        }
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
