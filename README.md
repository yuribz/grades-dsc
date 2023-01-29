## DSC Courses: Assignment Grades
A general framework to use automated pipelines to enter grades according to the Canvas roster.

Author: Yacun Wang, December 2022

---
### General Information
#### Code Requirements
- Python 3
- Jupyter Notebook with Python kernel
- Python Packages:
  - Canvas API: `pip install canvasapi`
  - `numpy`
  - `pandas`
- Canvas Administrative Access (TA or Instructor)
- Administrative Access to third-party sites

#### Pipeline Notebook Content
- **Setup**: 
  - **Canvas Setup**: For accessing new course information from Canvas API
  - **Personnel Setup**: Student/Staff Profiles, Email History
    - Updates student roster file from Canvas
    - Reads in staff roster
    - Reads in mismatched email history `.json` file  
- **Assignment Cells**: Cells designated to currently supported assignment types
- **Student Search** and **Debug Results**
  - For manually inspecting undetected emails from student roster and gradebook
  - Insert and preview current list of mismatched emails
  - Save as mismatched email file for later use

#### Workspace Outline
- **Note**: This is a sample workspace only. Remember to change paths in the script if you prefer using a different workspace.
```
grades_dsc/
├── .info/                        <- credentials
│   ├── canvas_credentials.json
│   ├── email_records.json
│   └── students.csv
├── archive/                      <- raw files
├── processed/                    <- processed gradebook
├── src/                          <- source code
│   ├── gradebook.py              <- general class
│   └── third_parties.py          <- customized classes
├── enter_grades.ipynb            <- main notebook
└── README.md
```
---
### New Course Setup

- Get Canvas course ID: `https://canvas.ucsd.edu/courses/<course_id>`
- Get Canvas API Key (if you don't have an unexpired one):
  - Log into Canvas, find `Account` on the left menu
  - Navigate to `Account > Settings`, scroll down to `+ New Access Token`
  -  Fill in `Purpose` and `Expire Date`. The key could possibly last forever
  -  Click `Generate`. You should be able to see the new API key under `Approved Integrations` and receive an email from Canvas.
- Create a new assignment group:
  - Manually navigate to your course, select `Assignments`
  - Use the top right button `+ Group` to create a new assignment group. This will be the `assignment_group` argument passed into the constructor of your desired assignment
- Put course ID and API key into `.info/canvas_credentials.json`.
- Finally, obtain a CSV of staff information of the following format, and place the file path in the staff profiles cell.

| First Name | Last Name | Email        | PID (Optional) |
| ---------- | --------- | ------------ | -------------- | 
| Roger     | Roy  | abc@ucsd.edu |                |
| Roy        | Roger     | def@ucsd.edu |                |
| ...        | ...       | ...          |                |
---
### Usage Documentation
#### Obtain Raw File
- Slido:
  - Log into `sli.do` using administrative credentials provided by instructor
  - Find the correct lecture poll title
  - Under the `Analytics` pane, click `Export => Download Export => Poll Results per user => XLS => Save` to download the file to your default download directory
  - Move this file under **the same directory** as the pipeline notebook (not archive)
- Zybook:
  - Log into Zybook using administrative credentials and select `Reporting` on the bottom-right corner
  - On the left pane, select the sections assigned
  - On the right pane, select `Entire Class` and set the deadline
  - Click `Download Report` and move the file under **the same directory** as the pipeline notebook
- Gradescope:
  - For assignments that the gradescope assignment score is exactly the same as the Canvas assignment score, please use the `link assignment` feature; for other assignments such as those having lateness or checkpoints, follow along.
  - Log into Gradescope using administrative credentials and select the main assignment page from the course
  - Find `Download Grades` and select `Download CSV` (could be in `More`)
  - If lateness is needed, create a question with 1 rubric item per deduction level; download the graded rubric by `Export Evaluations` and find the csv file for the question
  - If other sections such as checkpoint are needed, do `Download Grades > Download CSV` from the other assignment
  - For all downloaded files, move them under **the same directory** as the pipeline notebook

#### Gradebook Documentations
- `Gradebook` General Class: Defined in `gradebook.py`
  - Constructor Arguments:
    - `course`: `Canvas.course` object, obtained from setup
    - `students`: `pd.DataFrame`, obtained from personnel setup
    - `staff`: `pd.DataFrame`, obtained from personnel setup
    - `email_records`: `dict`, obtained from personnel setup
    - `file_name`: `str`, the main assignment file name
    - `assignment_name`: `str`, the assignment name showed on Canvas, and the name of the score column on gradebook
    - `dir_name`: `str`, the name of the sub-directory under `processed`
    - `assignment_group`: `str`, the name of the assignment group on Canvas; must be exact string match
    - `assignment_points`: `int`, the total points possible for the assignment
    - `due_time`: `str`, the due datetime string in the format of `'yyyy-mm-dd hh:mm'`, in 24-hour format; `None` if no due date is needed
  - Main Methods to implement:
    - `convert_raw(self, **kwargs)`: Reads the raw file and cleans the dataframe
    - `compute_grade(self, **kwargs)`: Computes the assignment grade according to the cleaned file
    - `create_gradebook(self, **kwargs)`: Use the two functions above and creates a `pd.DataFrame` as the gradebook output, with information such as email, name, assignment grade, etc. Also creates a file under `processed` directory for records. Could be overridden to use the above 2 functions differently
    - `enter_grades(self)`: Use the produced gradebook, create a Canvas assignment and input grades for each student. Could be overridden.
- `Slido` class: Defined in `third_parties.py`
  - Default Behaviors:
    - `dir_name`: `'slido'`
    - `assignment_group`: `'Lecture Participation'`
    - `assignment_points`: `1`
    - `due_time`: `None` (no change)
  - Grading Rubric: Gets 1 point if answered at least 75% of the polls, otherwise 0 points
- `Zybook` class: Defined in `third_parties.py`
  - Default Behaviors:
    - `dir_name`: `'readings'`
    - `assignment_group`: `'Readings'`
    - `assignment_points`: `5`
    - `due_time`: `None`
  - Required Configuration: `dict`, where keys are sections in strings and values are lists of activities assigned for the sections. Pass in `config=config`.
    - Example:
    ```
    config = {
        '1.2': ['Participation'],
        '1.3': ['Participation', 'Challenge'],
        '1.4': ['Challenge']
    }
    ```
  - Note: Discussion Zylabs should also use this class, with suggested `dir_name='zylab'` and `assignment_group='Discussion Zylab'`

- `Gradebook_Advanced` Class: Defined in `third_parties.py`
  - Additional Constructor Arguments:
    - `lateness_file`: `str`, file name of the lateness question; set to `None` if no lateness needed; default `None`
    - `other_section_files`: `dict`, where keys will be used as column names and values are corresponding section file names; default `None`
  - Default Behaviors:
    - `dir_name`: `'homework'`
    - `assignment_group`: `'Homework'`
    - `assignment_points`: `100`
    - `due_time`: `None`
  - Required if lateness exists: `dict`, where keys are keywords that are part of the rubric item strings and values are deduct percentages. Pass in `late_policy=late_policy`.
    - Example:
    ```
    late_policy = {
        'no late': 1.0,  # no deduction
        '1 day': 0.8,    # take 20% off
        '2 days': 0.5
    }
    ```

#### Run Pipeline
- General Procedure
  - Run all cells in `Setup`
  - Find the assignment type to transfer, change the parameters defined in the cell, and possibly other parameters listed above
  - Run the cell containing `create_gradebook` and inspect the produced gradebook dataframe, use `pandas` commands if needed
  - If the gradebook looks good, run the cell below to `enter_grades`
  - After everything is done, move the raw file under the `archive` directory for records
- Notes:
  - The `enter_grades` process will take a while as Canvas API only supports entering grade 1 student at a time
  - If the assignment is created successfully, you will receive Gmail and Canvas notifications if they are turned on
  - If the cell raises a `RuntimeError` about having no access to Canvas, interrupt the kernel, go to Canvas to manually delete the new assignment created, and rerun the cell.
- Resolve undetected emails
  - The pipeline will print all mismatched emails to the console, mostly because students are following the class but have no access to Canvas (ignore) or made typos to their email
  - Use the `Student Search` section to find the student name, processed results
    - Check for `@ucsd.edu` vs. `@gmail.com` or others
    - Check for mistyped names
    - Use your Gmail and type the email in recepients to check for possible matches
    - Use some creativity
    - **Note**: If you are really unable to find the student, ignore the mismatched email
  - Navigate to Canvas, select `Grades`, find the student and the assignement, and manually change the grade by clicking on that cell and type the new grade
  - Record the new mismatched email into `EMAIL_RECORDS` in the `Debug Results` section
    - The dictionary has where key is the mismatched email and value is the correct email
    - Run the `json.dump` cell to update the local file

#### Student Request to Check Grade: Slido
- Sometimes students will ask why they missed a lecture on the forum or via email
- Locate their information from both the raw file and the processed file in `archive` and `processed` directories respectively
- Remind them that 6 total grades will be dropped, and participation only worth 2%, so missing a few lectures is not affecting the grade by a lot (also applicable to late-enrolled students)
- From Marina:
  > These grades end up not affecting anyone after the final grade is posted if students miss a few lectures. Students could request checking final grade after the quarter ends, but none find participation grade essential.
- Sample Respond Format:
  > Hi! I have checked the sli.do record for you, and it seemed like you were missing Question X, leading to ?/? questions answered. Note that you need to answer at least 75% of the questions to get the credit. Please make sure that you click submit for every question, and then later actions such as changing answers should not affect the existence of your answers. But no worries since you have 6 lectures to drop throughout the quarter. Hope this helps!!
---
### Customization
The entire pipeline could be customized in the following ways:
- Change the default behaviors to the desired
- Change the source code to change the behavior
- Add new assignment types (e.g. Google Forms, Stepik, etc.) by inheriting the `Gradebook` class and implement the `__init__`, `convert_raw`, `compute_grades`, `create_gradebook`, and `enter_grades` methods.
---
### Resources
- Gradescope: [Link Canvas course and push grades](https://help.gradescope.com/article/y10z941fqs-instructor-canvas)
- Canvas API: [Python Documentation](https://canvasapi.readthedocs.io/en/stable/)
- Canvas API: [Full REST API](https://canvas.instructure.com/doc/api/)

