import {
  Activity,
  ArrowRight,
  Play,
  Target,
  Upload,
  Video,
} from 'lucide-react';
import { useState } from 'react';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Card } from './ui/card';

interface ModernHomePageProps {
  onGetStarted: () => void;
  onViewVideos: () => void;
  hasVideos: boolean;
}

export default function ModernHomePage({
  onGetStarted,
  onViewVideos,
  hasVideos,
}: ModernHomePageProps) {
  const [isHovering, setIsHovering] = useState<string | null>(null);

  const features = [
    {
      icon: Target,
      title: 'Ball Detection',
      description:
        'Advanced YOLO-powered ball tracking that detects and follows tennis balls throughout your videos with high accuracy.',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      detail: 'Real-time Tracking',
    },
    {
      icon: Activity,
      title: 'Pose Estimation',
      description:
        'MediaPipe pose detection with 33 keypoints to analyze your stroke technique, form, and body positioning.',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      detail: '11 Tennis Keypoints',
    },
    {
      icon: Video,
      title: 'Annotated Videos',
      description:
        'Generate videos with real-time overlays showing ball detection and pose estimation for comprehensive analysis.',
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      detail: 'Visual Overlays',
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      {/* Split Hero Section */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 to-purple-600/5" />

        <div className="relative max-w-7xl mx-auto px-6 py-16 sm:py-20">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Column - Text Content */}
            <div className="text-left">
              {/* Logo/Brand */}
              <div className="flex items-center mb-6">
                <div className="w-12 h-12 rounded-xl brand-gradient flex items-center justify-center mr-3">
                  <Target className="h-6 w-6 text-white" />
                </div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  Tennis Coach App
                </h1>
              </div>

              {/* Main Headline */}
              <div className="space-y-4 mb-8">
                <h2 className="text-4xl sm:text-5xl font-bold text-slate-900">
                  Perfect Your Tennis
                  <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                    {' '}
                    Technique
                  </span>
                </h2>
                <p className="text-lg text-slate-600 leading-relaxed">
                  Upload tennis videos for AI-powered analysis and instant
                  insights on your technique and performance.
                </p>
              </div>

              {/* CTA Buttons */}
              <div className="flex flex-col sm:flex-row gap-4">
                <Button
                  size="lg"
                  onClick={onGetStarted}
                  className="brand-gradient hover:shadow-lg transform hover:scale-105 transition-all duration-200 px-8 py-4 text-lg"
                  onMouseEnter={() => setIsHovering('upload')}
                  onMouseLeave={() => setIsHovering(null)}
                >
                  <Upload className="h-5 w-5 mr-2" />
                  Upload Video
                  <ArrowRight
                    className={`h-4 w-4 ml-2 transition-transform duration-200 ${
                      isHovering === 'upload' ? 'translate-x-1' : ''
                    }`}
                  />
                </Button>

                <Button
                  variant="outline"
                  size="lg"
                  onClick={onViewVideos}
                  className="px-8 py-4 text-lg border-2 hover:bg-slate-50"
                >
                  <Play className="h-5 w-5 mr-2" />
                  View Videos
                </Button>
              </div>
            </div>

            {/* Right Column - Feature Highlights */}
            <div className="grid gap-4">
              {features.map((feature, index) => (
                <div
                  key={index}
                  className="flex items-center gap-4 p-4 bg-white/80 backdrop-blur-sm rounded-xl border border-slate-200/60 shadow-sm hover:shadow-md transition-all duration-200"
                >
                  <div
                    className={`w-10 h-10 rounded-lg ${feature.bgColor} flex items-center justify-center shrink-0`}
                  >
                    <feature.icon className={`h-5 w-5 ${feature.color}`} />
                  </div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold text-slate-900 text-sm">
                      {feature.title}
                    </h4>
                    <Badge variant="secondary" className="text-xs">
                      {feature.detail}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Features Section */}
      <div className="py-16 bg-white/70">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-12">
            <h3 className="text-2xl font-bold text-slate-900 mb-3">
              Detailed Analysis Features
            </h3>
            <p className="text-slate-600">
              Explore the complete capabilities of our tennis analysis platform
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <Card
                key={index}
                className="p-8 border border-slate-200/60 bg-white/80 backdrop-blur-sm shadow-lg hover:shadow-xl hover:border-slate-300/60 hover:-translate-y-1 cursor-pointer group transition-all duration-300"
                onMouseEnter={() => setIsHovering(`detailed-${index}`)}
                onMouseLeave={() => setIsHovering(null)}
              >
                <div
                  className={`w-14 h-14 rounded-xl ${feature.bgColor} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-200`}
                >
                  <feature.icon className={`h-7 w-7 ${feature.color}`} />
                </div>

                <div className="space-y-4">
                  <h4 className="text-xl font-semibold text-slate-900">
                    {feature.title}
                  </h4>
                  <p className="text-slate-600 leading-relaxed">
                    {feature.description}
                  </p>
                </div>

                <div
                  className={`mt-6 opacity-0 group-hover:opacity-100 transition-opacity duration-200`}
                >
                  <Button
                    variant="ghost"
                    size="sm"
                    className={`${feature.color} hover:bg-transparent`}
                  >
                    Learn more
                    <ArrowRight className="h-3 w-3 ml-1" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
