import Image from "next/image";
import React from "react";

const Loading = () => {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="animate-pulse">
        <Image
          src="/loading.png"
          alt="Loading..."
          width={100}
          height={100}
        />
      </div>
    </div>
  );
};

export default Loading;