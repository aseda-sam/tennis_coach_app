import React from 'react';
import { useNavigate } from 'react-router-dom';
import DemoLanding from '../DemoLanding';
import { useAuth } from '../../hooks/useAuth';
import { useUploadModal } from '../layouts/AppLayout';

function HomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { openUploadModal, openVideoModal } = useUploadModal();

  const handleUploadVideo = () => {
    const profile = process.env.REACT_APP_PROFILE || 'local';
    if (profile === 'local' || user) {
      openUploadModal();
    } else {
      navigate('/library');
    }
  };

  return (
    <div className="app-container">
      <DemoLanding
        onTryDemo={() => navigate('/demo')}
        onUploadVideo={handleUploadVideo}
        onWatchTutorial={openVideoModal}
        user={user}
      />
    </div>
  );
}

export default HomePage;
