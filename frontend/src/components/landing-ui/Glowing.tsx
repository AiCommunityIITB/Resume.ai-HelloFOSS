"use client";

import { BrainCircuit, FastForward,  MessageCirclePlus,  SearchCheck, UserRoundSearch } from "lucide-react";
import { GlowingEffect } from "@/components/ui/glowing-effect";

export function GlowingEffectDemo() {
  return (
    <ul className="grid grid-cols-1 grid-rows-none gap-4 md:grid-cols-11 md:grid-rows-3 lg:gap-4 xl:max-h-[34rem] xl:grid-rows-2">
      <GridItem
        area="md:[grid-area:1/1/2/7] xl:[grid-area:1/1/2/5]"
        icon={<BrainCircuit className="h-4 w-4 text-black dark:text-neutral-400" />}
        title="AI-Powered Analysis"
        description="Advanced Machine learning algorithms analyze your resume against top companies standards"
      />

      <GridItem
        area="md:[grid-area:1/7/2/13] xl:[grid-area:2/1/3/5]"
        icon={<FastForward className="h-4 w-4 text-black dark:text-neutral-400" />}
        title="Get your analysis in Seconds"
        description="Resume Rater analyzes your resume within few seconds and saves your time"
      />

      <GridItem
        area="md:[grid-area:2/1/3/7] xl:[grid-area:1/5/3/8]"
        icon={<MessageCirclePlus className="h-4 w-4 text-black dark:text-neutral-400" />}
        title="Provides descriptive feedback and Suggestions"
        description="The AI suggests various changes in your Resume to make it more accurate."
      />

      <GridItem
        area="md:[grid-area:2/7/3/13] xl:[grid-area:1/8/2/12]"
        icon={<UserRoundSearch className="h-4 w-4 text-black dark:text-neutral-400" />}
        title="Get Personalized Recommendations "
        description="Personalised recommendations based on your history. "
      />

      <GridItem
        area="md:[grid-area:3/1/4/13] xl:[grid-area:2/8/3/12]"
        icon={<SearchCheck className="h-4 w-4 text-black dark:text-neutral-400" />}
        title="Bias Free scoring"
        description="The AI scores only on the basis of the relevence of your resume points to the sector which you are targetting, Hence avoing any other biases."
      />
    </ul>
  );
}
interface GridItemProps {
  area: string;
  icon: React.ReactNode;
  title: string;
  description: React.ReactNode;
}


const GridItem = ({ area, icon, title, description }: GridItemProps) => {
  return (
    <li className={`min-h-[14rem] m-5 list-none ${area}`}>
      <div className="relative h-full rounded-2xl border p-2 md:rounded-3xl md:p-3">
        <GlowingEffect
          blur={0}
          borderWidth={3}
          spread={80}
          glow={true}
          disabled={false}
          proximity={64}
          inactiveZone={0.01}
        />
        <div className="border-0.75 relative flex h-full flex-col justify-between gap-6 overflow-hidden rounded-xl p-6 md:p-6 dark:shadow-[0px_0px_27px_0px_#2D2D2D]">
          <div className="relative flex flex-1 flex-col justify-between gap-3">
            <div className="w-fit rounded-lg border border-gray-600 p-2">
              {icon}
            </div>
            <div className="space-y-3">
              <h3 className="-tracking-4 pt-0.5 font-sans text-xl/[1.375rem] font-semibold text-balance text-black md:text-2xl/[1.875rem] dark:text-white">
                {title}
              </h3>
              <h2 className="font-sans text-sm/[1.125rem] text-black md:text-base/[1.375rem] dark:text-neutral-400 [&_b]:md:font-semibold [&_strong]:md:font-semibold">
                {description}
              </h2>
            </div>
          </div>
        </div>
      </div>
    </li>
  );
};
