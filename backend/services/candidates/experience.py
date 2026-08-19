from datetime import datetime
from typing import List
from services.documents.schemas import ParsedEmployment
from dateutil import parser

class ExperienceCalculator:
    @staticmethod
    def _parse_date(date_str: str, default_to_now: bool = False) -> datetime:
        if not date_str:
            return datetime.now() if default_to_now else None
            
        if date_str.lower() in ['present', 'current', 'now']:
            return datetime.now()
            
        try:
            return parser.parse(date_str)
        except Exception:
            return None

    @staticmethod
    def calculate_total_experience(employments: List[ParsedEmployment]) -> float:
        """
        Deterministically calculates total years of experience, handling overlaps.
        """
        if not employments:
            return 0.0
            
        intervals = []
        for emp in employments:
            start = ExperienceCalculator._parse_date(emp.start_date)
            end = ExperienceCalculator._parse_date(emp.end_date, default_to_now=True)
            
            if start and end and start <= end:
                intervals.append((start, end))
                
        if not intervals:
            return 0.0
            
        # Merge overlapping intervals
        intervals.sort(key=lambda x: x[0])
        merged = [intervals[0]]
        
        for current in intervals[1:]:
            last = merged[-1]
            if current[0] <= last[1]:
                # Overlap, update the end date of the last interval if necessary
                merged[-1] = (last[0], max(last[1], current[1]))
            else:
                merged.append(current)
                
        # Calculate total days
        total_days = sum((end - start).days for start, end in merged)
        return round(total_days / 365.25, 2)
