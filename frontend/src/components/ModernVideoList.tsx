import {
  Activity,
  ArrowLeft,
  Clock,
  CloudUpload,
  Eye,
  FileText,
  Grid3X3,
  List,
  Play,
  Plus,
  Trash2,
  Upload,
} from 'lucide-react';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  analysisApi,
  AnalysisData,
  AnalysisStartResponse,
  videoApi,
} from '../services/api';
import { VideoMetadata } from '../types/video';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Progress } from './ui/progress';

interface ModernVideoListProps {
  onVideoDeleted?: () => void;
  onViewAnalysis?: (video: VideoMetadata) => void;
  onUpload?: () => void;
  onBack?: () => void;
}

const ModernVideoList: React.FC<ModernVideoListProps> = ({
  onVideoDeleted,
  onViewAnalysis,
  onUpload,
  onBack,
}) => {
  const [videos, setVideos] = useState<VideoMetadata[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [isDragging, setIsDragging] = useState(false);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  // Track active analysis tasks
  const [activeTasks, setActiveTasks] = useState<
    Map<
      number,
      {
        taskId: number;
        progress: number;
        status: string;
        currentStage?: string;
        stageProgress?: number;
      }
    >
  >(new Map());

  // Fetch videos and analyses
  const fetchVideos = useCallback(async () => {
    try {
      setLoading(true);
      const [videosData, analysesData] = await Promise.all([
        videoApi.getVideos(),
        analysisApi.getAllAnalyses(),
      ]);
      setVideos(videosData.videos);
      setAnalyses(analysesData);
      setError(null);
    } catch (err) {
      setError('Failed to load videos');
      console.error('Error fetching videos:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVideos();
  }, [fetchVideos]);

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!dropZoneRef.current?.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const videoFiles = files.filter((file) => file.type.startsWith('video/'));

    if (videoFiles.length > 0 && onUpload) {
      onUpload();
    }
  };

  const handleDeleteVideo = async (videoId: number) => {
    if (!window.confirm('Are you sure you want to delete this video?')) return;

    try {
      setDeletingId(videoId);
      await videoApi.deleteVideo(videoId);
      await fetchVideos();
      onVideoDeleted?.();
    } catch (err) {
      console.error('Error deleting video:', err);
      alert('Failed to delete video');
    } finally {
      setDeletingId(null);
    }
  };

  const startAnalysis = async (videoId: number) => {
    try {
      const response: AnalysisStartResponse = await analysisApi.startAnalysis(
        videoId,
        { analysis_type: 'full' }
      );

      // Add to active tasks
      setActiveTasks(
        (prev) =>
          new Map(
            prev.set(videoId, {
              taskId: response.task_id || 0,
              progress: 0,
              status: 'started',
              currentStage: 'Starting analysis...',
              stageProgress: 0,
            })
          )
      );

      // Start polling for this task
      if (response.task_id) {
        pollTaskProgress(videoId, response.task_id);
      }
    } catch (err) {
      console.error('Error starting analysis:', err);
      alert('Failed to start analysis');
    }
  };

  const pollTaskProgress = async (videoId: number, taskId: number) => {
    const poll = async () => {
      try {
        const progressData = await analysisApi.getTaskStatus(taskId);

        setActiveTasks((prev) => {
          const newMap = new Map(prev);
          newMap.set(videoId, {
            taskId,
            progress: progressData.progress,
            status: progressData.status,
            currentStage: progressData.current_stage || undefined,
            stageProgress: progressData.stage_progress || undefined,
          });
          return newMap;
        });

        if (
          progressData.status === 'SUCCESS' ||
          progressData.status === 'FAILURE'
        ) {
          setActiveTasks((prev) => {
            const newMap = new Map(prev);
            newMap.delete(videoId);
            return newMap;
          });

          // Refresh data
          await fetchVideos();
          return;
        }

        // Continue polling
        setTimeout(poll, 2000);
      } catch (err) {
        console.error('Error polling task progress:', err);
        setActiveTasks((prev) => {
          const newMap = new Map(prev);
          newMap.delete(videoId);
          return newMap;
        });
      }
    };

    poll();
  };

  const getStatusBadge = (video: VideoMetadata, analysis?: AnalysisData) => {
    const task = activeTasks.get(video.id);

    if (task) {
      return (
        <Badge className="bg-orange-50 text-orange-700 border-orange-200 hover:bg-orange-50">
          Processing
        </Badge>
      );
    }

    if (analysis) {
      return (
        <Badge className="bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-50">
          Analyzed
        </Badge>
      );
    }

    return (
      <Badge className="bg-green-50 text-green-700 border-green-200 hover:bg-green-50">
        Ready
      </Badge>
    );
  };

  const getVideoAnalysis = (videoId: number) => {
    return analyses.find((analysis) => analysis.video_id === videoId);
  };

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'Unknown';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  const formatDuration = (seconds?: number): string => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const VideoCard = ({ video }: { video: VideoMetadata }) => {
    const analysis = getVideoAnalysis(video.id);
    const task = activeTasks.get(video.id);

    return (
      <Card className="group overflow-hidden glass border-0 hover-lift">
        <div className="relative aspect-video bg-gradient-to-br from-blue-500 to-purple-600 overflow-hidden">
          <div className="w-full h-full bg-gray-200 flex items-center justify-center">
            <Play className="h-12 w-12 text-gray-400" />
          </div>
          <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />

          {/* Status Badge */}
          <div className="absolute top-3 left-3">
            {getStatusBadge(video, analysis)}
          </div>

          {/* Duration */}
          <div className="absolute bottom-3 right-3">
            <Badge className="bg-black/50 text-white border-0 hover:bg-black/50 backdrop-blur-sm">
              {formatDuration(video.duration)}
            </Badge>
          </div>

          {/* Play Button */}
          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-200">
            <Button
              size="lg"
              className="bg-white/20 backdrop-blur-sm border-white/30 text-white hover:bg-white/30 rounded-full w-14 h-14"
              onClick={() => onViewAnalysis?.(video)}
            >
              <Play className="h-5 w-5 ml-0.5" />
            </Button>
          </div>
        </div>

        <div className="p-5">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-slate-900 truncate mb-2">
                {video.filename}
              </h3>
              <p className="text-sm text-slate-500 flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5" />
                {new Date(video.created_at).toLocaleDateString()}
              </p>
            </div>

            <div className="flex items-center gap-2">
              {!analysis && !task && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => startAnalysis(video.id)}
                  className="text-blue-600 border-blue-600 hover:bg-blue-50"
                >
                  <Activity className="h-3 w-3 mr-1" />
                  Analyze
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-slate-400 hover:text-slate-600"
                onClick={() => handleDeleteVideo(video.id)}
                disabled={deletingId === video.id}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="space-y-3 text-sm">
            <div className="grid grid-cols-2 gap-3 text-slate-600">
              <div>
                <span className="text-slate-400">Size:</span>
                <span className="ml-1 font-medium">
                  {formatFileSize(video.file_size)}
                </span>
              </div>
              <div>
                <span className="text-slate-400">Resolution:</span>
                <span className="ml-1 font-medium">
                  {video.width && video.height
                    ? `${video.width}x${video.height}`
                    : 'Unknown'}
                </span>
              </div>
            </div>

            {task && (
              <div className="p-3 bg-orange-50 rounded-lg border border-orange-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-orange-800">
                    Processing...
                  </span>
                  <span className="text-sm text-orange-600">
                    {Math.round(task.progress)}%
                  </span>
                </div>
                <Progress value={task.progress} className="h-1.5 mb-2" />
                {task.currentStage && (
                  <p className="text-xs text-orange-600">{task.currentStage}</p>
                )}
              </div>
            )}

            {analysis && (
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-blue-700 text-sm font-medium">
                  Analysis Complete
                </p>
                <p className="text-blue-600 text-xs mt-1">
                  {analysis.frames_with_pose || 0} poses detected in{' '}
                  {analysis.total_frames || 0} frames
                </p>
              </div>
            )}
          </div>
        </div>
      </Card>
    );
  };

  const VideoListItem = ({ video }: { video: VideoMetadata }) => {
    const analysis = getVideoAnalysis(video.id);
    const task = activeTasks.get(video.id);

    return (
      <Card className="p-5 glass border-0 hover:shadow-md transition-all duration-200 group">
        <div className="flex items-center gap-5">
          <div className="relative w-28 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg overflow-hidden flex-shrink-0">
            <div className="w-full h-full bg-gray-200 flex items-center justify-center">
              <Play className="h-8 w-8 text-gray-400" />
            </div>
            <div className="absolute bottom-2 right-2">
              <Badge className="bg-black/50 text-white text-xs border-0 hover:bg-black/50 backdrop-blur-sm">
                {formatDuration(video.duration)}
              </Badge>
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <h3 className="font-semibold text-slate-900 truncate">
                {video.filename}
              </h3>
              {getStatusBadge(video, analysis)}
            </div>

            {task ? (
              <div className="mb-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-orange-700">Processing...</span>
                  <span className="text-sm text-orange-600">
                    {Math.round(task.progress)}%
                  </span>
                </div>
                <Progress value={task.progress} className="h-1.5" />
              </div>
            ) : analysis ? (
              <p className="text-sm text-blue-600 mb-3">
                Analysis complete - {analysis.frames_with_pose || 0} poses
                detected
              </p>
            ) : (
              <p className="text-sm text-slate-600 mb-3">Ready for analysis</p>
            )}

            <div className="flex items-center gap-6 text-sm text-slate-500">
              <span>Size: {formatFileSize(video.file_size)}</span>
              <span>
                Resolution:{' '}
                {video.width && video.height
                  ? `${video.width}x${video.height}`
                  : 'Unknown'}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {new Date(video.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {analysis ? (
              <Button
                size="sm"
                onClick={() => onViewAnalysis?.(video)}
                className="brand-gradient hover:shadow-md text-white"
              >
                <Eye className="h-4 w-4 mr-2" />
                View Analysis
              </Button>
            ) : !task ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => startAnalysis(video.id)}
                className="text-blue-600 border-blue-600 hover:bg-blue-50"
              >
                <Activity className="h-4 w-4 mr-2" />
                Start Analysis
              </Button>
            ) : null}

            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 text-slate-400 hover:text-slate-600"
              onClick={() => handleDeleteVideo(video.id)}
              disabled={deletingId === video.id}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600">Loading videos...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 flex items-center justify-center">
        <Card className="p-8 max-w-md text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <Button onClick={fetchVideos}>Try Again</Button>
        </Card>
      </div>
    );
  }

  return (
    <div
      ref={dropZoneRef}
      className={`min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 transition-all duration-300 ${
        isDragging ? 'bg-blue-50/50' : ''
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            {onBack && (
              <Button
                variant="ghost"
                onClick={onBack}
                className="text-slate-600 hover:text-slate-900"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Home
              </Button>
            )}
            <div>
              <h1 className="text-3xl font-bold text-slate-900 mb-2">
                My Videos
              </h1>
              <p className="text-slate-600">
                {videos.length} video{videos.length !== 1 ? 's' : ''} uploaded
                {activeTasks.size > 0 && (
                  <span className="ml-2 text-blue-600">
                    • {activeTasks.size} processing
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* View Mode Toggle */}
            <div className="flex items-center glass rounded-lg p-1 border-0">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
                className={
                  viewMode === 'grid'
                    ? 'bg-white shadow-sm'
                    : 'hover:bg-white/50'
                }
              >
                <Grid3X3 className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('list')}
                className={
                  viewMode === 'list'
                    ? 'bg-white shadow-sm'
                    : 'hover:bg-white/50'
                }
              >
                <List className="h-4 w-4" />
              </Button>
            </div>

            <Button
              onClick={onUpload}
              className="brand-gradient hover:shadow-lg"
            >
              <Plus className="h-4 w-4 mr-2" />
              Upload Video
            </Button>
          </div>
        </div>

        {/* Drag Overlay */}
        {isDragging && (
          <div className="fixed inset-0 bg-blue-600/10 backdrop-blur-sm z-50 flex items-center justify-center">
            <Card className="p-8 glass border-2 border-dashed border-blue-300 max-w-md text-center">
              <div className="w-16 h-16 mx-auto bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <CloudUpload className="h-8 w-8 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Drop to Upload
              </h3>
              <p className="text-slate-600">
                Release to upload your tennis videos
              </p>
            </Card>
          </div>
        )}

        {/* Videos Grid/List */}
        {videos.length === 0 ? (
          <Card className="p-12 text-center glass border-2 border-dashed border-slate-200">
            <div className="w-16 h-16 mx-auto bg-slate-100 rounded-full flex items-center justify-center mb-6">
              <FileText className="h-8 w-8 text-slate-400" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-3">
              No videos uploaded yet
            </h3>
            <p className="text-slate-600 mb-8 max-w-md mx-auto">
              Get started by uploading your first tennis video for AI-powered
              analysis and technique insights.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button
                onClick={onUpload}
                className="brand-gradient hover:shadow-lg"
              >
                <Upload className="h-4 w-4 mr-2" />
                Upload Your First Video
              </Button>
            </div>
            <p className="text-sm text-slate-500 mt-6">
              Or simply drag and drop video files anywhere on this page
            </p>
          </Card>
        ) : (
          <div
            className={
              viewMode === 'grid'
                ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
                : 'space-y-4'
            }
          >
            {videos.map((video) =>
              viewMode === 'grid' ? (
                <VideoCard key={video.id} video={video} />
              ) : (
                <VideoListItem key={video.id} video={video} />
              )
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ModernVideoList;
