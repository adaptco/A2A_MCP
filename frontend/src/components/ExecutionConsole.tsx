import React from 'react';

const ExecutionConsole: React.FC = () => {
  return (
    <div>
      <h2>Execution Console</h2>
      <div style={{ border: '1px solid black', height: '200px', overflowY: 'scroll' }}>
        {/* Execution output will go here */}
      </div>
    </div>
  );
};

export default ExecutionConsole;
