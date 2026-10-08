"use client";

import Header from "@/components/Header";
import { AnimatedPinDemo } from "@/components/landing-ui/SignIn";
import { ThreeDCardDemo } from "@/components/landing-ui/3dCard";
import { GlowingEffectDemo } from "@/components/landing-ui/Glowing";
import { CardHoverEffectDemo } from "@/components/landing-ui/Hover-effect";
import SpiderMan from "@/components/ui/SpiderMan";

export default function Home() {
  return (
    <main className="overflow-x-hidden bg-black min-h-screen">
      {/* Header */}
      <div className="absolute left-0 top-0 w-full z-50">
        <Header />
      </div>
      
      {/* Hero Section */}
      <section id="Home" className="relative w-full min-h-screen flex flex-col justify-center items-center xl:flex-row xl:justify-around xl:items-center">
        <SpiderMan />
        
        <div className="pb-10 xl:pb-0 xl:pt-20 z-10">
          
          <div className="font-extrabold w-[80vw] sm:w-[60vw] xl:w-[35vw] text-4xl text-gray-200 sm:text-5xl md:text-6xl xl:text-6xl leading-tight">
            Want to assess your{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-600 to-white">
              Resume
            </span>
            ?
          </div>
          <div className="mt-6 text-lg font-medium w-[80vw] sm:w-[60vw] xl:w-[35vw] text-gray-300 md:text-xl xl:text-2xl pt-10">
            Introducing Insti's AI-based Resume Rater
          </div>
          <div className="mt-6 text-lg font-medium w-[80vw] sm:w-[60vw] xl:w-[35vw] text-gray-300 md:text-xl xl:text-2xl">
            Rizz your resume with{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-600 to-white">
              Rizzume
            </span>
          </div>
        </div>

        <div className="flex justify-center mt-10 xl:mt-0">
          <div className="w-70 sm:w-90">
            <AnimatedPinDemo />
          </div>
        </div>
      </section>

      {/* About Section */}
      <section id="About" className="w-full min-h-screen py-20">
        <div className="container mx-auto px-6 lg:px-15">
          <div className="flex flex-col justify-center items-center xl:flex-row xl:justify-around xl:items-center min-h-screen">
            
            {/* About Text */}
            <div className="pb-15 xl:pb-0 text-center xl:text-left">
              <h2 className="font-extrabold text-4xl sm:text-5xl md:text-6xl">
                <span className="text-white">About the </span>
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-600 to-white">
                  Product
                </span>
              </h2>
              <p className="mt-8 text-xl text-gray-300 max-w-lg">
                Resume Rater is an AI-based application that rates your resume after analyzing the document, 
                providing comprehensive feedback to help you improve your career prospects.
              </p>
            </div>

            {/* Feature Cards */}
            <div className="flex flex-col md:flex-row justify-center gap-6 mt-10 xl:mt-0">
              <div className="mx-3 my-5">
                <ThreeDCardDemo 
                  title="Upload your Resume" 
                  text="Upload your .pdf formatted resume and mention the sector you are targeting." 
                  link="./images/Upload.webp"
                />
              </div>
              <div className="mx-3 my-5">
                <ThreeDCardDemo 
                  title="Get AI analyzed report" 
                  text="AI rates your Resume based on your resume's relevance in the target sector." 
                  link="/logo.png"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Glowing Effect Section */}
      <section className="w-full py-20">
        <div className="container mx-auto px-[10vw] xl:px-[10vw]">
          <div className="flex items-center justify-center min-h-[400px]">
            <GlowingEffectDemo />
          </div>
        </div>
      </section>

      {/* AI Model Section */}
      <section id="Ai" className="min-h-screen w-full py-20">
        <div className="container mx-auto xl:my-20">
          {/* Section Title */}
          <div className="flex justify-center xl:justify-start xl:ml-[12vw] mb-16">
            <h2 className="font-extrabold text-4xl sm:text-5xl md:text-6xl">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-600 to-white">
                AI{" "}
              </span>
              <span className="text-white">Model</span>
            </h2>
          </div>
          
          {/* AI Model Cards */}
          <div className="px-[10vw]">
            <div className="w-full flex justify-center pb-20">
              <CardHoverEffectDemo />
            </div>
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section id="contact" className="w-full min-h-screen bg-gradient-to-b from-black to-gray-900 py-20">
        <div className="container mx-auto px-6 xl:my-20">
          {/* Section Title */}
          <div className="flex justify-center xl:justify-start xl:ml-[12vw] mb-16">
            <h2 className="font-extrabold text-4xl sm:text-5xl md:text-6xl text-transparent bg-clip-text bg-gradient-to-r from-cyan-600 to-white">
              Contacts
            </h2>
          </div>
          
          {/* Contact Content */}
          <div className="flex justify-center">
            <div className="xl:w-[50vw]">
            <div className="flex flex-col items-center xl:items-start space-y-8 xl:w-[50vw]">
            <h3 className="text-3xl text-center font-semibold text-white w-[50vw]">Managers</h3>
            <div className="space-y-6 flex flex-col xl:space-y-0 xl:justify-around xl:w-[50vw] xl:flex-row ">
              <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700 hover:border-cyan-500 transition-colors duration-300 w-60">
                <h4 className="text-xl font-medium text-cyan-400">AI Community IIT Bombay</h4>
                <p className="text-gray-300 mt-2">GitHub: AiCommunityIITB</p>
              </div>
              
              <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700 hover:border-cyan-500 transition-colors duration-300 w-60">
                <h4 className="text-xl font-medium text-cyan-400">HelloFOSS Contributions</h4>
                <p className="text-gray-300 mt-2">Open an issue in this repository</p>
              </div>
              </div>
            </div>
           
            {/* Additional Contact Info */}
            <div className="mt-12 text-center  xl:w-[50vw]">
              <p className="text-gray-400 text-lg ">
                Have questions? Feel free to reach out to our team for support and inquiries.
              </p>
            </div>
           </div>
          </div>
        </div>
      </section>
    </main>
  );
}
