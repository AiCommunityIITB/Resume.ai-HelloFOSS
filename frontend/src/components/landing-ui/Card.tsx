"use client"; // if it's a client component

import React from "react";
import {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

export default function CardExample() {
  return (
    <Card className="border">
      <CardHeader className="border-b">
        <CardTitle>My Card Title</CardTitle>
        <CardAction>...</CardAction>
        <CardDescription>This is a description.</CardDescription>
      </CardHeader>
      <CardContent>
        <p>Some content inside the card.</p>
      </CardContent>
      <CardFooter className="border-t">
        <p>Footer content</p>
      </CardFooter>
    </Card>
  );
}
