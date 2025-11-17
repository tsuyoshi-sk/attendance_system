import React from 'react';
import { Calendar } from 'lucide-react';
import PageHeader from '../components/Layout/PageHeader';

const CalendarPage: React.FC = () => {
  return (
    <div>
      <PageHeader
        title="カレンダー"
        description="月別の勤怠カレンダービュー"
      />

      <div className="card">
        <div className="card-content py-24 text-center text-slate-500">
          <Calendar size={64} className="mx-auto mb-4 opacity-30" />
          <h3 className="text-lg font-medium text-slate-700 mb-2">開発中</h3>
          <p>カレンダービューは現在開発中です</p>
        </div>
      </div>
    </div>
  );
};

export default CalendarPage;
