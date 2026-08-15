export function VegIndicator({ isVeg }: { isVeg: boolean }) {
  return (
    <span
      className={
        "flex h-3.5 w-3.5 shrink-0 items-center justify-center border " +
        (isVeg ? "border-success-600" : "border-danger-600")
      }
      aria-label={isVeg ? "Vegetarian" : "Non-vegetarian"}
      title={isVeg ? "Veg" : "Non-veg"}
    >
      <span className={"h-1.5 w-1.5 rounded-full " + (isVeg ? "bg-success-600" : "bg-danger-600")} />
    </span>
  );
}
