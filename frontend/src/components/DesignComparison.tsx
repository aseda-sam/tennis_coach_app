import { Activity, BarChart3, Eye, Target, Zap } from 'lucide-react';
import { useState } from 'react';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Card } from './ui/card';

export default function DesignComparison() {
  const [activeTab, setActiveTab] = useState<'old' | 'new'>('new');

  const OldDesign = () => (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="app-container">
        <div className="upload-section">
          <h1 className="app-title">Tennis Video Analyzer</h1>
          <p className="app-subtitle">
            Upload your tennis videos for advanced performance analysis and
            technique insights
          </p>
          <div className="view-videos-section">
            <button className="view-videos-btn">View My Videos</button>
          </div>
        </div>
      </div>
    </div>
  );

  const NewDesign = () => (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 to-purple-600/5" />

        <div className="relative max-w-7xl mx-auto px-6 pt-20 pb-16">
          <div className="text-center">
            {/* Logo/Brand */}
            <div className="flex items-center justify-center mb-8">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl brand-gradient flex items-center justify-center">
                  <Target className="h-6 w-6 text-white" />
                </div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  Tennis Video Analyzer
                </h1>
              </div>
            </div>

            {/* Main Headline */}
            <div className="space-y-6 mb-12">
              <h2 className="text-4xl sm:text-5xl font-bold text-slate-900 max-w-4xl mx-auto">
                Perfect Your Tennis
                <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  {' '}
                  Technique
                </span>
              </h2>
              <p className="text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
                Upload your tennis videos for advanced AI-powered analysis. Get
                instant insights on technique, form, and performance metrics to
                elevate your game.
              </p>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
              <Button
                size="lg"
                className="brand-gradient hover:shadow-lg transform hover:scale-105 transition-all duration-200 px-8 py-4 text-lg"
              >
                Start Analysis
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="px-8 py-4 text-lg border-2 hover:bg-slate-50"
              >
                View My Videos
              </Button>
            </div>

            {/* Sample Analysis Cards */}
            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              <Card className="p-6 glass border-0 hover-lift">
                <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center mb-4">
                  <Target className="h-6 w-6 text-blue-600" />
                </div>
                <h3 className="font-semibold text-slate-900 mb-2">
                  AI-Powered Analysis
                </h3>
                <p className="text-slate-600 text-sm mb-4">
                  Advanced computer vision analyzes every frame for detailed
                  insights.
                </p>
                <Badge variant="secondary" className="text-xs">
                  99.2% accuracy
                </Badge>
              </Card>

              <Card className="p-6 glass border-0 hover-lift">
                <div className="w-12 h-12 rounded-xl bg-green-50 flex items-center justify-center mb-4">
                  <BarChart3 className="h-6 w-6 text-green-600" />
                </div>
                <h3 className="font-semibold text-slate-900 mb-2">
                  Performance Tracking
                </h3>
                <p className="text-slate-600 text-sm mb-4">
                  Track progress with comprehensive analytics and
                  recommendations.
                </p>
                <Badge variant="secondary" className="text-xs">
                  15+ metrics
                </Badge>
              </Card>

              <Card className="p-6 glass border-0 hover-lift">
                <div className="w-12 h-12 rounded-xl bg-purple-50 flex items-center justify-center mb-4">
                  <Zap className="h-6 w-6 text-purple-600" />
                </div>
                <h3 className="font-semibold text-slate-900 mb-2">
                  Instant Results
                </h3>
                <p className="text-slate-600 text-sm mb-4">
                  Get comprehensive analysis results within seconds of upload.
                </p>
                <Badge variant="secondary" className="text-xs">
                  &lt;30s processing
                </Badge>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-white">
      {/* Tab Navigation */}
      <div className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">
              Design Comparison
            </h1>
            <div className="flex gap-2">
              <Button
                variant={activeTab === 'old' ? 'default' : 'outline'}
                onClick={() => setActiveTab('old')}
              >
                Current Design
              </Button>
              <Button
                variant={activeTab === 'new' ? 'default' : 'outline'}
                onClick={() => setActiveTab('new')}
                className="brand-gradient text-white"
              >
                ✨ New Design (Figma-Inspired)
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      {activeTab === 'old' ? <OldDesign /> : <NewDesign />}

      {/* Comparison Notes */}
      <div className="bg-gray-50 border-t border-gray-200 p-8">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-6">
            Key Improvements in New Design
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <Eye className="h-5 w-5 text-blue-600" />
                <h3 className="font-semibold">Visual Hierarchy</h3>
              </div>
              <ul className="text-sm text-gray-600 space-y-2">
                <li>• Modern gradients and glassmorphism</li>
                <li>• Better typography with brand colors</li>
                <li>• Improved spacing and layout</li>
              </ul>
            </Card>

            <Card className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <Activity className="h-5 w-5 text-green-600" />
                <h3 className="font-semibold">Interactions</h3>
              </div>
              <ul className="text-sm text-gray-600 space-y-2">
                <li>• Hover animations and micro-interactions</li>
                <li>• Better button states and feedback</li>
                <li>• Smooth transitions</li>
              </ul>
            </Card>

            <Card className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <Target className="h-5 w-5 text-purple-600" />
                <h3 className="font-semibold">Components</h3>
              </div>
              <ul className="text-sm text-gray-600 space-y-2">
                <li>• Tailwind CSS + Shadcn/ui components</li>
                <li>• Consistent design system</li>
                <li>• Reusable and maintainable</li>
              </ul>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
