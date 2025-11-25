export const intensityToColor = (intensity?: string) => {
  switch (intensity) {
    case "high":
      return "bg-red-500/20 text-red-700";
    case "medium":
      return "bg-amber-400/30 text-amber-700";
    case "low":
      return "bg-emerald-400/20 text-emerald-700";
    default:
      return "bg-slate-200 text-slate-700";
  }
};
