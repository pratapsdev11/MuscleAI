"use client"

import { useState } from "react"
import { Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"

export function UploadForm() {
  const [exerciseType, setExerciseType] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [message, setMessage] = useState("")
  const [videoUrl, setVideoUrl] = useState("")
  const [avgInjuryProbability, setAvgInjuryProbability] = useState<number | null>(null)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !exerciseType) return

    const formData = new FormData()
    formData.append("video", file)
    formData.append("exercise_type", exerciseType)

    try {
      const response = await fetch("http://localhost:5000/", {
        method: "POST",
        body: formData,
      })

      const data = await response.json()
      
      if (data.message) {
        setMessage(data.message)
      }
      if (data.video_url) {
        setVideoUrl(data.video_url)
      }
      if (data.avg_injury_probability !== undefined) {
        setAvgInjuryProbability(data.avg_injury_probability)
      }
    } catch (error) {
      setMessage("Error uploading video. Please try again.")
      console.error("Upload error:", error)
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="exercise-type">Exercise Type</Label>
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

        <div className="space-y-2">
          <Label htmlFor="video">Video Upload</Label>
          <div className="flex items-center justify-center w-full">
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer hover:bg-muted">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <Upload className="w-8 h-8 mb-2 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  {file ? file.name : "Click to upload or drag and drop"}
                </p>
              </div>
              <input
                id="video"
                name="video"
                type="file"
                className="hidden"
                accept="video/*"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
          </div>
        </div>

        <Button type="submit" className="w-full" disabled={!file || !exerciseType}>
          Upload and Analyze
        </Button>
      </form>

      {message && (
        <p className="text-sm text-muted-foreground">{message}</p>
      )}

      {videoUrl && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Processed Video:</h2>
          <video width="600" controls className="w-full rounded-lg">
            <source src={`http://localhost:5000/static/${videoUrl}`} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>
      )}

      {avgInjuryProbability !== null && (
        <div className="mt-4">
          <h2 className="text-lg font-semibold">
            Average Injury Probability: {avgInjuryProbability}
          </h2>
        </div>
      )}
    </div>
  )
}

