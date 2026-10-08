
import { HoverEffect } from "../ui/card-hover-effect";
import { BrainCircuit,CircleCheckBig,Lightbulb ,ChartColumnStacked} from "lucide-react";
export function CardHoverEffectDemo() {
  return (
    <div className="w-325 mx-3 px-3">
      <HoverEffect items={projects} />
    </div>
  );
}
export const projects = [
  { icon:<BrainCircuit className="h-4 w-4 text-black dark:text-neutral-400" />,
    title: "Trained on multiple Resumes",
    description:
      "Resume rater has been trained on more than 500 Resumes for precise scoring",
    link: "https://.com",
  },
  {  icon:<ChartColumnStacked className="h-4 w-4 text-black dark:text-neutral-400" />,
    title: " Compares with Top Resumes in the Sector",
    description:
      "The score is calculated by measuring how similar your Resume is similar to top resumes applied.",
    link: "https://.com",
  },
  
 
  { icon:<CircleCheckBig className="h-4 w-4 text-black dark:text-neutral-400" />,
    title: "Score based on other aspects",
    description:
      "Other aspects such as formatting,typos,etc. are also taken into account.",
    link: "https://.com",
  },
  { icon:<Lightbulb className="h-4 w-4 text-black dark:text-neutral-400" />,
    title: "Provides suggestions by using RL",
    description:
      "Reinforcement Learning is used to provide recommendations to the user.",
    link: "https://.com",
  },
];
