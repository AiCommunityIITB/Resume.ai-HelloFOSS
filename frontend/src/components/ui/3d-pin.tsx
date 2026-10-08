// "use client";
// import React, { useState } from "react";
// import { cn } from "@/lib/utils";


// export const PinContainer = ({
//   children,
 
//   href,
//   className,
//   containerClassName,
// }: {
//   children: React.ReactNode;
//   title?: string;
//   href?: string;
//   className?: string;
//   containerClassName?: string;
// }) => {
//   const [transform, setTransform] = useState(
//     "translate(-50%,-50%) rotateX(0deg)"
//   );

//   const onMouseEnter = () => {
//     setTransform("translate(-50%,-50%) rotateX(20deg) scale(0.8)");
//   };
//   const onMouseLeave = () => {
//     setTransform("translate(-50%,-50%) rotateX(0deg) scale(1)");
//   };

//   return (
//     <a
//       className={cn(
//         "relative group/pin z-50  cursor-pointer",
//         containerClassName
//       )}
//       onMouseEnter={onMouseEnter}
//       onMouseLeave={onMouseLeave}
//       href={href || "/"}
//     >
//       <div
//         style={{
//           perspective: "1000px",
        
//         }}
//         className="relative"
//       >
//         <div
//           style={{
//             transform: transform,
//           }}
//           className="relative p-4 flex justify-start items-start rounded-2xl shadow-[0_8px_16px_rgb(0_0_0/0.4)] bg-black border border-white/[0.1] group-hover/pin:border-white/[0.2] transition duration-700 overflow-hidden"
//         >
//           <div className={cn(" relative z-50 ", className)}>{children}</div>
//         </div>
//       </div>
      
//     </a>
//   );
// };
"use client";
import Link from 'next/link';
import React, { useState } from "react";
import { cn } from "@/lib/utils";

export const PinContainer = ({
  children,
  href,
  className,
  containerClassName,
}: {
  children: React.ReactNode;
  title?: string;
  href?: string;
  className?: string;
  containerClassName?: string;
}) => {
  const [transform, setTransform] = useState("rotateX(0deg)");

  const onMouseEnter = () => {
    setTransform("rotateX(20deg) scale(0.95)");
  };
  const onMouseLeave = () => {
    setTransform("rotateX(0deg) scale(1)");
  };

  return (
    <Link
      className={cn("relative group/pin z-0 cursor-pointer", containerClassName)}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      href={href || "/"}
    >
      <div
        style={{ perspective: "1000px" }}
        className="relative overflow-hidden rounded-2xl"
      >
        <div
          style={{ transform }}
          className="p-4 flex justify-start items-start rounded-2xl shadow-[0_8px_16px_rgb(0_0_0/0.4)] bg-black border border-white/[0.1] group-hover/pin:border-white/[0.2] transition duration-700"
        >
          <div className={cn("z-0", className)}>{children}</div>
        </div>
      </div>
    </Link>
  );
};
