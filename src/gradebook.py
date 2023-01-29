"""
General Gradebook Class: DSC Grades
"""

import numpy as np
import time
import os
from datetime import datetime

class Gradebook:
    """
    A general purpose Gradebook suitable for any third party
    activities that could download a spreadsheet representing
    records for each student and will be loaded into Canvas.
    """
    
    def __init__(
        self, course, students, staff, email_records,
        file_name, assignment_name, dir_name, 
        assignment_group, assignment_points, due_time=None
    ):
        # names
        self.assignment_name = assignment_name
        self.file_name = file_name
        self.dir_name = dir_name
        
        # personnel record
        self.course = course
        self.students = students
        self.staff = staff
        self.email_records = email_records
        
        # assignment details
        self.assignment_group_name = assignment_group
        self.assignment_group_id = self.find_assignment_group_id()
        self.assignment_points = assignment_points
        self.due_time = due_time
        
        # processed
        self.gradebook = None        
        
    def find_assignment_group_id(self):
        """
        Finds the group ID shown on Canvas.
        """
        for group in self.course.get_assignment_groups():
            if group.name == self.assignment_group_name:
                return group.id
        
        # create new group
        new_group = self.course.create_assignment_group({
            'name': self.assignment_group_name
        }) 
        return new_group.id
    
    def convert_raw(self, **kwargs):
        """
        Defines how to process raw files into pd.DataFrame
        """
        raise NotImplementedError
        
    def compute_grade(self, **kwargs):
        """
        Defines how grade is computed based on dataframe
        """
        raise NotImplementedError
        
    def create_gradebook(self, **kwargs):
        """
        Based on dataframe and grading rubric, create gradebook with student
        score and answer history
        """
        # create record
        self.convert_raw(**kwargs)
        self.compute_grade(**kwargs)
        self.gradebook['email'] = self.gradebook['typed_email'].apply(
            lambda s: self.email_records[s] if s in self.email_records else s
        )
        
        # join with students
        self.gradebook = (
            self.students
            .merge(self.gradebook, on='email', how='outer')
            .set_index('email')
        )
        self.gradebook[self.assignment_name] = self.gradebook[self.assignment_name].fillna(0)
        
        # save records
        proc_name = (
            self.assignment_name
            .lower()
            .replace(' (', '_')
            .replace('/', '')
            .replace(')', '')
            .replace(' ', '')
        )
        
        # optional: create directory
        if not os.path.exists('processed'):
            os.mkdir('processed')
        if not os.path.exists(os.path.join('processed', self.dir_name)):
            os.mkdir(f'processed/{self.dir_name}')
        
        self.gradebook.to_csv(f'processed/{self.dir_name}/{proc_name}.csv')
        return self.gradebook
    
    def enter_grades(self):
        """
        Based on gradebook, creates Canvas assignment and enters grade.
        Also prints mismatched emails to console.
        """
        print(f"Processing {self.assignment_group_name}: {self.assignment_name}")
        
        # create canvas assignment
        assignment_exist = False
        works = self.course.get_assignments_for_group(assignment_group=self.assignment_group_id)
        for work in works:
            if work.name == self.assignment_name:
                assignment_exist = True
                new_assignment = work
        
        if not assignment_exist:
            new_assignment = self.course.create_assignment({
                'name': self.assignment_name,
                'grading_type': 'points',
                'due_at': (
                    datetime
                    .strptime(self.due_time, '%Y-%m-%d %H:%M')
                    .strftime('%Y-%m-%dT%H:%M:00-07:00')
                ) if self.due_time is not None else None,
                'notify_of_update': False,
                'points_possible': self.assignment_points,
                'published': True,
                'assignment_group_id': self.assignment_group_id
            })

        # process grade
        students_update = self.gradebook[
            (~self.gradebook.index.isin(self.staff)) & 
            (~self.gradebook['id'].isna())
        ]
        grade_updates = (
            students_update
            [[self.assignment_name]]
            .rename(columns={
                self.assignment_name: 'posted_grade'
            })
            .set_index(students_update['id'].astype(int).astype(str))
            .to_dict('index')
        )
        progress = new_assignment.submissions_bulk_update(**grade_updates)
        self.track_progress(progress)
        print()

        # return mismatches
        print('Email Mismatches:')
        return self.gradebook[self.gradebook['id'].isna()]

    def track_progress(self, progress):
        while progress.completion != 100:
            if progress.workflow_state == 'failed':
                print('Progress Failed, Restart Workflow')
            else:
                time.sleep(5)
        print('Progress Completed')