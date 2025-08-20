import React from 'react';
import { Button } from './ui/button';
import { Card, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Upload, Play, BarChart3, Trophy } from 'lucide-react';

interface ModernHomePageProps {
  onGetStarted: () => void;
  onViewVideos: () => void;
  hasVideos: boolean;
}

const ModernHomePage: React.FC<ModernHomePageProps> = ({
  onGetStarted,
  onViewVideos,
  hasVideos,
}) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-4">
            Tennis Coach
            <span className="text-blue-600"> AI</span>
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Advanced video analysis powered by artificial intelligence to improve your tennis game
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                <Upload className="w-6 h-6 text-blue-600" />
              </div>
              <CardTitle>Upload Videos</CardTitle>
              <CardDescription>
                Upload your tennis videos for instant AI analysis
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                <BarChart3 className="w-6 h-6 text-green-600" />
              </div>
              <CardTitle>AI Analysis</CardTitle>
              <CardDescription>
                Get detailed insights on your technique and performance
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                <Trophy className="w-6 h-6 text-purple-600" />
              </div>
              <CardTitle>Improve Faster</CardTitle>
              <CardDescription>
                Track your progress and identify areas for improvement
              </CardDescription>
            </CardHeader>
          </Card>
        </div>

        {/* Action Buttons */}
        <div className="text-center space-y-4">
          {hasVideos ? (
            <div className="space-y-4">
              <Button 
                onClick={onViewVideos} 
                size="lg" 
                className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3"
              >
                <Play className="w-5 h-5 mr-2" />
                View My Videos
              </Button>
              <div>
                <Badge variant="secondary" className="text-sm">
                  You have videos ready for analysis
                </Badge>
              </div>
            </div>
          ) : (
            <Button 
              onClick={onGetStarted} 
              size="lg" 
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3"
            >
              <Upload className="w-5 h-5 mr-2" />
              Get Started
            </Button>
          )}
        </div>

        {/* Stats */}
        <div className="mt-16 grid md:grid-cols-3 gap-8 text-center">
          <div>
            <div className="text-3xl font-bold text-blue-600">1000+</div>
            <div className="text-gray-600">Videos Analyzed</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-green-600">95%</div>
            <div className="text-gray-600">Accuracy Rate</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-purple-600">24/7</div>
            <div className="text-gray-600">AI Processing</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModernHomePage;
