import React from 'react';
import OpenPointList from '../components/OpenPointList';
import OpenPointDetail from '../components/OpenPointDetail';
import CodeEditor from '../components/CodeEditor';
import ExecutionConsole from '../components/ExecutionConsole';

const MainPage: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <div style={{ display: 'flex', flex: 1 }}>
        <div style={{ flex: 1, borderRight: '1px solid black', padding: '10px' }}>
          <OpenPointList />
        </div>
        <div style={{ flex: 2, padding: '10px' }}>
          <OpenPointDetail />
          <CodeEditor />
          <ExecutionConsole />
        </div>
      </div>
    </div>
  );
};

export default MainPage;
