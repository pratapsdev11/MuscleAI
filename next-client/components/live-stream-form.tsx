"use client"

import { useState } from "react"
import { Video } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"

export function LiveStreamForm() {
  const [exerciseType, setExerciseType] = useState("")

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!exerciseType) return

    const formData = new FormData()
    formData.append("live_exercise_type", exerciseType)

    try {
      const response = await fetch("http://localhost:5000/live", {
        method: "POST",
        body: formData,
      })
      
      // Handle the live stream response as needed
      if (response.ok) {
        // Redirect or handle live stream initialization
        console.log("Live stream started")
      }
    } catch (error) {
      console.error("Live stream error:", error)
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="live-exercise-type">Exercise Type</Label>
        <Select value={exerciseType} onValueChange={setExerciseType}>
          <SelectTrigger>
            <SelectValue placeholder="Select exercise type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="regular_deadlift">Regular Deadlift</SelectItem>
            <SelectItem value="sumo_deadlift">Sumo Deadlift</SelectItem>
            <SelectItem value="squat">Squat</SelectItem>
            <SelectItem value="romanian_deadlift">Romanian Deadlift</SelectItem>
            <SelectItem value="zercher_squats">Zercher Squats</SelectItem>
            <SelectItem value="front_squat">Front Squats</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Button type="submit" className="w-full" disabled={!exerciseType}>
        <Video className="w-4 h-4 mr-2" />
        Start Live Session
      </Button>
    </form>
  )
}
