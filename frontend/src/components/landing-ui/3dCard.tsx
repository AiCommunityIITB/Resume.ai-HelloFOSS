"use client";

import React from "react";
import { CardBody, CardContainer, CardItem } from "@/components/ui/3d-card";
interface ThreeDCardDemoProps {
  title: string;
  text: string;
  link: string;
}


export function ThreeDCardDemo(props:ThreeDCardDemoProps) {
  return (
    <CardContainer className="inter-var">
      <CardBody className="bg-gray-50 relative group/card dark:hover:shadow-2xl dark:hover:shadow-emerald-500/[0.1] dark:bg-black dark:border-white/[0.2] border-black/[0.1] w-[18rem] sm:w-[23rem] h-80 rounded-xl p-5 border">
        <CardItem
          translateZ={50}
          className="text-2xl font-bold text-neutral-600 dark:text-white"
        >
         {props.title}
        </CardItem>
        <CardItem
          as="p"
          translateZ={60}
          className="text-neutral-500 w-full mt-2 dark:text-neutral-300"
        >
         {props.text}
        </CardItem>
        <CardItem translateZ={100} className="w-full mt-4">
          <img
            src={props.link}
            height={1000}
            width={1000}
            className="h-45 w-full object-cover rounded-xl group-hover/card:shadow-xl"
            alt="thumbnail"
          />
        </CardItem>
        <div className="flex justify-between items-center mt-8">
         
         
        </div>
      </CardBody>
    </CardContainer>
  );
}
