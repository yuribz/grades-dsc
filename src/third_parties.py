"""
Party-Specific Gradebook Classes
DSC Courses
"""

import numpy as np
import pandas as pd
import os
import re
from datetime import datetime
from gradebook import Gradebook


class Slido(Gradebook):
    """
    Online lecture participation polls conducted on sli.do

    Canvas Assignment Group (Default): Lecture Participation
    Credit per Lecture: 1
    Drop per Quarter: 6
    Processed File Location (Default): `./processed/slido`
    Lateness: None
    """

    def __init__(
        self, course, students, staff, email_records,
        file_name, assignment_name,
        dir_name='slido',
        assignment_group='Lecture Participation'
    ):
        super().__init__(
            course, students, staff, email_records,
            file_name, assignment_name,
            dir_name=dir_name,
            assignment_group=assignment_group,
            assignment_points=1
        )

    def convert_raw(self, **kwargs):
        """
        An excel format spreadsheet with answer records for each question
        """
        self.gradebook = (
            pd.read_excel(self.file_name, header=0, skiprows=[1])
            .drop(columns=["User ID", "User Name", "User company", "Total Correct Answers"])
            .rename(columns={'User Email': "typed_email"})
        )

    def compute_grade(self, min_poll=0.75, **kwargs):
        """
        With n questions polled, each student is expected to answer at least 75%
        to get credit for that lecture
        """
        self.gradebook[self.assignment_name] = (
            self.gradebook
            .drop(columns=['typed_email'])
            .isna()
            .mean(axis=1) <= (1 - min_poll)
        ) * 1


class Zybook(Gradebook):
    """
    Zybook activities, including Participation, Challenge, ZyLab.
    Note: Please pass config dict[str]:List[str] to `create_gradebook(config=config)`
    Example:
    ```
    config = {
        '1.2': ['Participation'],
        '1.3': ['Participation', 'Challenge'],
        '1.4': ['Challenge']
    }
    ```

    ### Reading Activities
    Canvas Assignment Group (Default): Readings
    Credit per Lecture: 5
    Drop per Quarter: 3
    Processed File Location (Default): `./processed/readings`
    Lateness: None

    ### Discussion Zylab
    Canvas Assignment Group: Discussion Zylab
    Credit per Lecture: 5
    Drop per Quarter: 3
    Processed File Location: `./processed/zylab`
    Lateness: None
    """

    def __init__(
        self, course, students, staff, email_records,
        file_name, assignment_name,
        dir_name='readings',
        assignment_group='Readings',
        due_time=None
    ):
        super().__init__(
            course, students, staff, email_records,
            file_name, assignment_name,
            dir_name=dir_name,
            assignment_group=assignment_group,
            assignment_points=5,
            due_time=due_time
        )

    def convert_raw(self, **kwargs):
        """
        A csv format spreadsheet with completed scores for each section
        """
        # load
        df = pd.read_csv(self.file_name)

        # create string pattern
        pat = '|'.join([
            f'((?:{sec} - {act}) \(([0-9]+)\))'
            for sec, req in kwargs['config'].items()
            for act in req
        ])

        # find columns
        col_info = [
            list(filter(None, capture[0]))
            for capture in (re.findall(pat, col) for col in df.columns)
            if len(capture) > 0
        ]
        self.total_score = sum(int(score) for _, score in col_info)
       
        # filter columns
        self.gradebook = pd.DataFrame({
            col: (df[col].fillna(0) * int(cred_str) / 100).round().astype(int)
            for col, cred_str in col_info
        }).assign(typed_email=df['Primary email'])

    def compute_grade(self, **kwargs):
        """
        With n total points in the sections assigned, determine grade out of 5 by percentage:
                  100: 5 points
            [80, 100): 4 points
             [60, 80): 3 points
             [40, 60): 2 points
             [20, 40): 1 point
              [0, 20): 0 points
        """
        self.gradebook['total_score'] = (
            self.gradebook
            .drop(columns=['typed_email'])
            .sum(axis=1)
        )
        self.gradebook['percentage'] = self.gradebook['total_score'] / self.total_score * 100
        self.gradebook[self.assignment_name] = self.gradebook['percentage'].apply(
            lambda score: (
                5 if score >= 93 
                else 4 if score >= 80
                else 3 if score >= 60
                else 2 if score >= 40
                else 1 if score >= 20
                else 0
            )
        )  


class Gradescope(Gradebook):
    """
    Gradescope assignements that have lateness and extra credits

    ### Homework
    Canvas Assignment Group (Default): Homework
    Credit per Assignment: 100
    Drop per Quarter: 1
    Processed File Location (Default): `./processed/homework`
    Lateness: 100-80-50-0

    ### Project
    Canvas Assignment Group: Project
    Credit per Assignment: 100
    Drop per Quarter: 0
    Processed File Location: `./processed/project`
    Lateness: 100-80-50-0
    """

    def __init__(
        self, course, students, staff, email_records,
        file_name, assignment_name, 
        lateness_policy=None,
        lateness_file=None,
        total_slip_days=None,
        other_section_files=None,
        dir_name='homework',
        assignment_group='Homework',
        assignment_points=100,
        due_time=None
    ):
        super().__init__(
            course, students, staff, email_records,
            file_name, assignment_name,
            dir_name=dir_name,
            assignment_group=assignment_group,
            assignment_points=assignment_points,
            due_time=due_time
        )
        assert (
            lateness_policy is None or 
            lateness_policy.lower() in ['penalty', 'slip_day']
        )
        self.lateness_policy = lateness_policy
        self.lateness_file = lateness_file
        self.total_slip_days = total_slip_days
        self.other_section_files = (
            {} if other_section_files is None
            else other_section_files
        )

    def convert_raw(self, **kwargs):
        """
        Pick out assignment-related columns from csv.
        """
        # load
        self.gradebook = pd.read_csv(self.file_name)
        self.lateness = pd.read_csv(self.lateness_file)
        self.lateness = self.lateness[self.lateness['Assignment Submission ID'].str.isnumeric()]
        self.other_sections = {name: pd.read_csv(fp) for name, fp in self.other_section_files.items()}

        # find columns
        self.gradebook = self.gradebook[['Email', 'Total Score']].rename(columns={
            'Total Score': 'assignment_score'
        }).fillna(0)
        self.gradebook[self.assignment_name] = self.gradebook['assignment_score']

        # process email errors
        self.gradebook['Email'] = self.gradebook['Email'].apply(
            lambda s: self.email_records[s] if s in self.email_records else s
        )

        # find lateness
        def late_category(s, policy):
            for category, factor in policy.items():
                if category in s.lower():
                    return factor

        if self.lateness_policy == 'penalty':
            if 'penalty_policy' in kwargs and kwargs['penalty_policy'] is not None: 
                # match policy
                policy = kwargs['penalty_policy']  
                late_cols = list(filter(
                    lambda col: any(p in col.lower() for p in policy),
                    self.lateness.columns
                ))
                self.lateness['late_factor'] = (
                    self.lateness[late_cols]
                    .astype(float)
                    .idxmax(axis=1)
                    .apply(late_category, args=(policy,))
                    .fillna(1.0)
                )

                # join main gradebook
                self.gradebook = self.gradebook.merge(
                    self.lateness[['Email', 'late_factor']], 
                    on='Email'
                )
            else:
                self.gradebook['late_factor'] = 1.0
        
        elif self.lateness_policy == 'slip_day':
            # process file
            self.lateness['slip_day'] = (
                self.lateness[['No Lateness', 'Slip Day Used']]
                .astype(float)
                .idxmax(axis=1)
                .apply(lambda s: 0 if s == 'No Lateness' else 1)
            ).astype(int)

            # join main gradebook
            self.gradebook = self.gradebook.merge(
                self.lateness[['Email', 'slip_day']], 
                on='Email'
            )

        # find other sections
        for name, sec in self.other_sections.items():
            sec = sec[['Email', 'Total Score']].copy()
            sec[name] = sec['Total Score'].fillna(0)
            self.gradebook = self.gradebook.merge(
                sec[['Email', name]], 
                on='Email'
            )
        
        # consistent
        self.gradebook = self.gradebook.rename(columns={'Email': 'email'})

    
    def compute_grade(self, **kwargs):
        """
        Applies late penalty or extra credit labelled as different assignment.
        """
        # process lateness
        if self.lateness_policy == 'penalty':     
            self.gradebook[self.assignment_name] *= self.gradebook['late_factor']
        
        # process other sections
        for name in self.other_sections:
            self.gradebook[self.assignment_name] += self.gradebook[name]


    def create_gradebook(self, **kwargs):
        """
        Based on dataframe and grading rubric, create gradebook with student
        score and answer history
        """
        # create record
        self.convert_raw(**kwargs)
        self.compute_grade(**kwargs)
        
        # join with students
        self.gradebook = (
            self.students
            .merge(self.gradebook, on='email', how='outer')
            .set_index('email')
        )
        self.gradebook[self.assignment_name] = self.gradebook[self.assignment_name].fillna(0)
        
        # save records
        proc_name = self.assignment_name
        
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

        Overrides Gradebook.enter_grades due to complicated assignment setting
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
                'submission_types': ["external_tool"],
                'external_tool_tag_attributes': {
                    "url": "https://www.gradescope.com/auth/lti/callback",
                    "new_tab": True
                },
                'grading_type': 'points',
                'due_at': (
                    datetime
                    .strptime(self.due_time, '%Y-%m-%d %H:%M')
                    .strftime('%Y-%m-%dT%H:%M:00-07:00')
                ),
                'notify_of_update': True,
                'points_possible': self.assignment_points,
                'published': True,
                'assignment_group_id': self.assignment_group_id
            })

        # process grade
        self.students_update = self.gradebook[
            (~self.gradebook.index.isin(self.staff)) & 
            (~self.gradebook['id'].isna())
        ].fillna(0)

        grade_updates = (
            self.students_update
            [[self.assignment_name]]
            .set_index(self.students_update['id'].astype(int).astype(str))
        )
        self.submit_grade(
            assignment=new_assignment,
            df=grade_updates,
            grade_col=self.assignment_name,
            log='Main Assignment'
        )
        print()
            
        # return mismatches
        return self.gradebook[self.gradebook['id'].isna()]
    

    def get_slip_day_assignment(self, students_initalize):
        """
        Finds the slip day assignment, or creates it if not existent
        """
        works = self.course.get_assignments_for_group(assignment_group=self.assignment_group_id)
        for work in works:
            if work.name == 'Slip Day Usage':
                return work
        
        # create new assignment
        new_slip_day_assignment = self.course.create_assignment({
            'name': 'Slip Day Usage',
            'grading_type': 'points',
            'notify_of_update': True,
            'points_possible': self.total_slip_days,
            'published': True,
            'assignment_group_id': self.assignment_group_id,
            'omit_from_final_grade': True,
            'description': open('src/slip_day_description.txt', 'r').read().strip()
        })

        # initialize 0 days used
        initial = pd.DataFrame(
            {'posted_grade': 0}, 
            index=students_initalize['id'].astype(int).astype(str)
        )
        self.submit_grade(
            assignment=new_slip_day_assignment,
            df=initial,
            grade_col='posted_grade',
            log='Initialize Slip Day'
        )
        return new_slip_day_assignment


    def process_slip_day(self):
        """
        Updates slip day assignment
        """
        
        print('Updating Slip Day Usage')
        slip_day_assignment = self.get_slip_day_assignment(self.students_update)

        # get last grade
        last_grade = pd.Series({
            str(sub.user_id): int(sub.grade) 
            for sub in slip_day_assignment.get_submissions()
            if sub.grade is not None
        }, dtype=int).to_frame(name='last_grade').fillna(0)

        # get new assignment slip day usage
        slip_day_updates = (
            self.students_update[['id', 'slip_day']]
            .set_index(self.students_update['id'].astype(int).astype(str))
            .drop(columns=['id'])
        )

        slip_day_updates = slip_day_updates.merge(
            last_grade,
            how='left',
            left_index=True,
            right_index=True
        ).fillna(0)

        silp_day_updates = slip_day_updates[slip_day_updates['slip_day'] > 0]

        slip_day_updates = (
            (
                silp_day_updates['slip_day'] + 
                silp_day_updates['last_grade']
            )
            .to_frame(name='posted_grade')
            .assign(comment=f'Slip Day Used in {self.assignment_name}')
        )

        # update slip day total
        self.submit_grade(
            assignment=slip_day_assignment,
            df=slip_day_updates,
            grade_col='posted_grade',
            comment_col='comment',
            log='Slip Day Assignment'
        )
