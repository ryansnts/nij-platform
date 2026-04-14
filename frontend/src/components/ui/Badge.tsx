import { cn } from "@/lib/utils";

type Color = "blue" | "green" | "red" | "yellow" | "gray";

const colors: Record<Color, string> = {
  blue:   "bg-blue-500/10 text-blue-400 border-blue-500/20",
  green:  "bg-green-500/10 text-green-400 border-green-500/20",
  red:    "bg-red-500/10 text-red-400 border-red-500/20",
  yellow: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  gray:   "bg-white/5 text-[var(--muted)] border-[var(--border)]",
};

export function Badge({ children, color = "gray", className }: {
  children: React.ReactNode; color?: Color; className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs border font-medium", colors[color], className)}>
      {children}
    </span>
  );
}
