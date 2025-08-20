import { Activity, ArrowLeft, Eye, TrendingUp } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useAnalysisManager } from '../hooks/useAnalysisManager';
import { videoApi } from '../services/api';
import { VideoMetadata } from '../types/video';
import AnalysisResults from './AnalysisResults';
import ProgressBar from './ProgressBar';
import StageProgress from './StageProgress';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Progress } from './ui/progress';
import VideoPlayer from './VideoPlayer';

interface ModernAnalysisDashboardProps {
  videoId: number;
  videoFilename: string;
  videoUrl: string;
  onClose: () => void;
}

const ModernAnalysisDashboard: React.FC<ModernAnalysisDashboardProps> = ({
  videoId,
  videoFilename,
  videoUrl,
  onClose,
}) => {
  const [aspectRatioMode, setAspectRatioMode] = useState<
    'cover' | 'contain' | 'auto'
  >('contain');

  const { analysisState, isLoading, cancelAnalysis } = useAnalysisManager({
    videoId,
    autoRefresh: true,
  });

  const { analysis, error, progress, status } = analysisState;
  const isPolling = status === 'processing';

  // Map status to ProgressBar compatible status
  const getProgressBarStatus = () => {
    switch (status) {
      case 'idle':
        return 'starting';
      case 'completed':
        return 'completed';
      default:
        return status;
    }
  };

  const [video, setVideo] = useState<VideoMetadata | null>(null);

  useEffect(() => {
    const fetchVideoDetails = async () => {
      try {
        const videoData = await videoApi.getVideo(videoId);
        setVideo(videoData);
      } catch (err) {
        console.error('Failed to fetch video details:', err);
      }
    };

    fetchVideoDetails();
  }, [videoId]);

  // Format relative time
  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) {
      return `${diffInSeconds} seconds ago`;
    } else if (diffInSeconds < 3600) {
      const minutes = Math.floor(diffInSeconds / 60);
      return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 86400) {
      const hours = Math.floor(diffInSeconds / 3600);
      return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else {
      const days = Math.floor(diffInSeconds / 86400);
      if (days === 1) {
        return 'Yesterday';
      } else if (days < 7) {
        return `${days} days ago`;
      } else {
        return date.toLocaleDateString();
      }
    }
  };

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  // Format duration
  const formatDuration = (seconds: number) => {
    if (!seconds) return 'N/A';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const getVideoUrl = () => {
    const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000/v0';
    if (analysis?.pose_detections && analysis.pose_detections.length > 0) {
      return `${baseUrl}/videos/${videoId}/annotated`;
    }
    return videoUrl;
  };

  // Only show analysis items that have real data
  const analysisItems = [];
  
  // Video Quality Assessment - always show if we have quality data
  if (video?.quality_level || video?.quality_score) {
    analysisItems.push({
      title: 'Video Quality Assessment',
      score: video?.quality_level ? video.quality_level.charAt(0).toUpperCase() + video.quality_level.slice(1) : 'Good',
      percentage: Math.round((video?.quality_score || 0.8) * 100),
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      icon: Eye,
    });
  }
  
  // Pose Detection - only show if we have real analysis data
  if (analysis?.pose_detection_rate !== undefined) {
    analysisItems.push({
      title: 'Pose Detection',
      score: `${(analysis.pose_detection_rate * 100).toFixed(1)}% DETECTED`,
      percentage: Math.round(analysis.pose_detection_rate * 100),
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200',
      icon: TrendingUp,
    });
  }
  
  // Ball Detection - only show if we have real analysis data
  if (analysis?.detection_rate !== undefined) {
    analysisItems.push({
      title: 'Ball Detection',
      score: `${(analysis.detection_rate * 100).toFixed(1)}% DETECTED`,
      percentage: Math.round(analysis.detection_rate * 100),
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200',
      icon: Activity,
    });
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <Button
            variant="ghost"
            onClick={onClose}
            className="text-slate-600 hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Videos
          </Button>
          <div className="text-right">
            <h1 className="text-xl font-semibold text-slate-900 truncate max-w-md">
              {videoFilename}
            </h1>
            <p className="text-slate-600">
              {video?.created_at ? formatRelativeTime(video.created_at) : 'Uploaded recently'}
            </p>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Video Player Section */}
          <div className="lg:col-span-2 space-y-6">
            {/* Display Mode Selector */}
            <Card className="p-4 bg-white/80 backdrop-blur-sm border-0 shadow-sm">
              <div className="flex items-center gap-4">
                <label className="text-sm font-medium text-slate-700">
                  Video Display Mode:
                </label>
                <select
                  value={aspectRatioMode}
                  onChange={(e) =>
                    setAspectRatioMode(
                      e.target.value as 'cover' | 'contain' | 'auto'
                    )
                  }
                  className="px-3 py-1 border border-slate-200 rounded-md bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="contain">Fit with Black Bars (Default)</option>
                  <option value="cover">Crop to Fit</option>
                  <option value="auto">Auto Adjust</option>
                </select>
              </div>
            </Card>

            {/* Video Player */}
            <Card className="overflow-hidden bg-black shadow-xl">
              <div className="relative aspect-video bg-black">
                <VideoPlayer
                  videoUrl={getVideoUrl()}
                  title={
                    analysis?.pose_detections &&
                    analysis.pose_detections.length > 0
                      ? `${videoFilename} (Annotated)`
                      : videoFilename
                  }
                  showControls={true}
                  aspectRatioMode={aspectRatioMode}
                />

                {/* AI Analysis Badge */}
                {analysis?.pose_detections &&
                  analysis.pose_detections.length > 0 && (
                    <div className="absolute top-4 left-4">
                      <Badge className="bg-blue-600 text-white hover:bg-blue-600">
                        <Activity className="h-3 w-3 mr-1" />
                        AI Analysis Active
                      </Badge>
                    </div>
                  )}
              </div>
            </Card>

            {/* Video Details */}
            <Card className="p-6 bg-white/80 backdrop-blur-sm border-0 shadow-sm">
              <h3 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <Eye className="h-5 w-5" />
                Video Details
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <label className="text-sm text-slate-600">File Size</label>
                  <p className="font-semibold">
                    {video?.file_size ? formatFileSize(video.file_size) : 'N/A'}
                  </p>
                </div>
                <div>
                  <label className="text-sm text-slate-600">Resolution</label>
                  <p className="font-semibold">
                    {video?.width && video?.height
                      ? `${video.width}×${video.height}`
                      : 'N/A'}
                  </p>
                </div>
                <div>
                  <label className="text-sm text-slate-600">Duration</label>
                  <p className="font-semibold">
                    {video?.duration ? formatDuration(video.duration) : 'N/A'}
                  </p>
                </div>
                <div>
                  <label className="text-sm text-slate-600">Status</label>
                  <div className="mt-1">
                    <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
                      {analysis ? 'Analysis Complete' : 'Ready for Analysis'}
                    </Badge>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Analysis Results */}
          <div className="space-y-6">
            <Card className="p-6 bg-white/80 backdrop-blur-sm border-0 shadow-sm">
              <h2 className="font-semibold text-slate-900 mb-6 flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-green-600" />
                Tennis Coach Analysis Results
              </h2>

              <div className="space-y-6">
                {analysisItems.map((item, index) => (
                  <div
                    key={index}
                    className={`p-4 rounded-xl border-2 ${item.bgColor} ${item.borderColor} transition-all duration-200 hover:shadow-sm`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center">
                          <item.icon className={`h-4 w-4 ${item.color}`} />
                        </div>
                        <h3 className="font-medium text-slate-900">
                          {item.title}
                        </h3>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Badge
                          className={`${item.bgColor} ${item.color} border-0 hover:${item.bgColor}`}
                        >
                          {item.score}
                        </Badge>
                        <span className={`text-sm font-semibold ${item.color}`}>
                          {item.percentage}%
                        </span>
                      </div>
                      <Progress value={item.percentage} className="h-2" />
                    </div>
                  </div>
                ))}
              </div>
            </Card>



            {/* Analysis Status Section - Show when analysis is running */}
            {(isLoading || isPolling) && (
              <Card className="p-6 bg-white/80 backdrop-blur-sm border-0 shadow-sm">
                <div className="text-center">
                  <div className="mb-4">
                    <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto"></div>
                  </div>
                  <h3 className="font-semibold text-slate-900 mb-2">
                    Analysis in Progress
                  </h3>
                  <p className="text-slate-600 text-sm mb-4">
                    AI is analyzing your tennis video. This may take a few
                    moments.
                  </p>

                  {progress && (
                    <div className="space-y-3">
                      <StageProgress
                        currentStage={
                          analysisState.currentStage || 'processing'
                        }
                        stageProgress={analysisState.stageProgress || 0}
                        stageMessage={
                          analysisState.stageMessage || 'Processing...'
                        }
                        overallProgress={progress}
                      />
                      <ProgressBar
                        progress={progress}
                        status={getProgressBarStatus()}
                      />
                    </div>
                  )}

                  <Button
                    variant="outline"
                    onClick={cancelAnalysis}
                    className="mt-4 text-red-600 border-red-600 hover:bg-red-50"
                  >
                    Cancel Analysis
                  </Button>
                </div>
              </Card>
            )}

            {/* Legacy Analysis Results Component */}
            {analysis && !isLoading && (
              <div className="hidden">
                <AnalysisResults
                  analysis={analysis}
                  video={video}
                  isLoading={isLoading}
                  error={error}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModernAnalysisDashboard;
