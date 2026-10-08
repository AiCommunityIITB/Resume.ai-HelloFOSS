"use client"
import { cn } from "@/lib/utils";

export const HoverEffect = ({
  items,
  className,
}: {
  items: {
    icon: React.ReactElement;
    title: string;
    description: string;
    link: string;
  }[];
  className?: string;
}) => {
  return (
    <div
      className={cn(
        "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 py-10 justify-items-center",
        className
      )}
    >
      {items.map((item, index) => (
        <a
          href={item?.link}
          // fallback to index if link is missing or not unique
          key={`${item?.link || "link-missing"}-${index}`}
          className="relative block p-2 h-90 w-full"
        >
          <Card>
            <Icon>{item.icon}</Icon>
            <CardTitle>{item.title}</CardTitle>
            <CardDescription>{item.description}</CardDescription>
          </Card>
        </a>
      ))}
    </div>
  );
};

export const Card = ({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) => {
  return (
    <div
      className={cn(
        "rounded-2xl h-90 w-full p-4 overflow-hidden bg-black border border-transparent dark:border-white/[0.3] relative z-0",
        className
      )}
    >
      <div className="relative z-0">
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
};

export const Icon = ({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) => {
  return (
    <div className={cn("h-8 w-8 border-solid border-1 rounded-md border-gray-400 flex justify-center pt-2", className)}>
      {children}
    </div>
  );
};

export const CardTitle = ({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) => {
  return (
    <h4 className={cn("text-zinc-100 font-semibold text-2xl tracking-wide mt-4", className)}>
      {children}
    </h4>
  );
};

export const CardDescription = ({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) => {
  return (
    <p
      className={cn(
        "mt-8 text-zinc-400 tracking-wide leading-relaxed text-sm",
        className
      )}
    >
      {children}
    </p>
  );
};
