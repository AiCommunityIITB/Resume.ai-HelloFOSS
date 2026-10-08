// "use client";
// import React, { useEffect, useRef, useState } from "react";
// import { motion, useScroll, useMotionValueEvent } from "motion/react";
// import { cn } from "@/lib/utils";

// interface StickyScrollProps {
//   content: {
//     title: string;
//     description: string;
//     content?: React.ReactNode;
//   }[];
//   contentClassName?: string;
// }

// export const StickyScroll: React.FC<StickyScrollProps> = ({
//   content,
//   contentClassName,
// }) => {
//   const [activeCard, setActiveCard] = useState(0);
//   const ref = useRef<HTMLDivElement>(null);

//   const { scrollYProgress } = useScroll({
//     container: ref,
//     offset: ["start start", "end start"],
//   });

//   const safeContent = content ?? [];
// const cardLength = safeContent.length;

// const cardsBreakpoints = React.useMemo(() => {
//   if (cardLength <= 0) return [];
//   if (cardLength === 1) return [0];
//   return safeContent.map((_, index) => index / (cardLength - 1));
// }, [cardLength]);

// useMotionValueEvent(scrollYProgress, "change", (latest) => {
//   if (!cardsBreakpoints.length) return;

//   const closestIndex = cardsBreakpoints.reduce((acc, breakpoint, index) => {
//     const accBreakpoint = cardsBreakpoints[acc] ?? 0;
//     const distance = Math.abs(latest - breakpoint);
//     const accDistance = Math.abs(latest - accBreakpoint);
//     return distance < accDistance ? index : acc;
//   }, 0);

//   setActiveCard(closestIndex);
// });


  

//   const backgroundColors = [
//     "#0f172a", // slate-900
//     "#000000", // black
//     "#171717", // neutral-900
//   ];
//   const linearGradients = [
//   "linear-gradient(to bottom right, #06b6d4, #10b981)", // cyan-500 to emerald-500
//   "linear-gradient(to bottom right, #ec4899, #6366f1)", // pink-500 to indigo-500
//   "linear-gradient(to bottom right, #f97316, #eab308)", // orange-500 to yellow-500
//   "linear-gradient(to bottom right, #3b82f6, #9333ea)", // blue-500 to purple-600 (new gradient)
// ];


//   const [backgroundGradient, setBackgroundGradient] = useState(linearGradients[0]);

//   useEffect(() => {
//     setBackgroundGradient(linearGradients[activeCard % linearGradients.length]);
//   }, [activeCard, linearGradients]);

//   return (
//     <motion.div
//       animate={{
//         backgroundColor: backgroundColors[activeCard % backgroundColors.length],
//       }}
//       className="relative flex h-[30rem] justify-center space-x-10 overflow-y-auto rounded-md p-10"
//       ref={ref}
//     >
//       <div className="relative flex items-start px-4">
//         <div className="max-w-2xl">
//           {content.map((item, index) => (
//             <div key={item.title + index} className="my-20">
//               <motion.h2
//                 initial={{ opacity: 0 }}
//                 animate={{ opacity: activeCard === index ? 1 : 0.3 }}
//                 className="text-2xl font-bold text-slate-100"
//               >
//                 {item.title}
//               </motion.h2>
//               <motion.p
//                 initial={{ opacity: 0 }}
//                 animate={{ opacity: activeCard === index ? 1 : 0.3 }}
//                 className="mt-10 max-w-sm text-slate-300"
//               >
//                 {item.description}
//               </motion.p>
//             </div>
//           ))}
//           <div className="h-40" />
//         </div>
//       </div>
//       <div
//         style={{ background: backgroundGradient }}
//         className={cn(
//           "sticky top-10 hidden h-60 w-80 overflow-hidden rounded-md bg-white lg:block",
//           contentClassName
//         )}
//       >
//         {content[activeCard]?.content ?? null}
//       </div>
//     </motion.div>
//   );
// };
"use client";
import React, { useRef, useState } from "react";
import { motion, useScroll, useMotionValueEvent } from "motion/react";

export const StickyScrollOne = () => {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    container: ref,
    offset: ["start start", "end start"],
  });

  const [active, setActive] = useState(0);

  useMotionValueEvent(scrollYProgress, "change", (latest) => {
    // your logic
    setActive(Math.round(latest * 10));
  });

  return (
    <motion.div ref={ref} className="h-96 overflow-y-auto bg-red-100">
      <div className="h-[200vh]">Scroll content One: Active = {active}</div>
    </motion.div>
  );
};

export const StickyScrollTwo = () => {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    container: ref,
    offset: ["start start", "end start"],
  });

  const [active, setActive] = useState(0);

  useMotionValueEvent(scrollYProgress, "change", (latest) => {
    setActive(Math.round(latest * 20));
  });

  return (
    <motion.div ref={ref} className="h-96 overflow-y-auto bg-green-100">
      <div className="h-[200vh]">Scroll content Two: Active = {active}</div>
    </motion.div>
  );
};

export const StickyScrollThree = () => {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    container: ref,
    offset: ["start start", "end start"],
  });

  const [active, setActive] = useState(0);

  useMotionValueEvent(scrollYProgress, "change", (latest) => {
    setActive(Math.round(latest * 30));
  });

  return (
    <motion.div ref={ref} className="h-96 overflow-y-auto bg-blue-100">
      <div className="h-[200vh]">Scroll content Three: Active = {active}</div>
    </motion.div>
  );
};
