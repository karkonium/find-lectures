import requests
import html
from bs4 import BeautifulSoup

# main goal: make a key-value pair of semester and courses that were offered in web-option

SEMESTERS_URL = 'https://www.utsc.utoronto.ca/weboption/participating-courses'
SEMESTERS = ['winter', 'summer', 'fall']
SEASON_TO_CODE = {
    'winter': '1',
    'summer': '5',
    'fall': '9'
}
CODE_TO_SEASON = {
    '1': 'winter',
    '5': 'summer',
    '9': 'fall'
}
AUTH_HEADER = {
    # can't put that on a open repo
}


def remove_non_alpha_num_char(string, preserve_space=False):
    """
    Remove all non-alphanuumeric characters from a string

    :param string: starting string
    :param preserve_space: preveses spaces if true
    :return: a formatted version of string param
    """

    return ''.join([i for i in string if i.isalpha() or i.isnumeric() or (preserve_space and i.isspace())])


def verify_working_link(link):
    """
    Check if the link works

    :param link: link you want to check
    :return: true if the link works, false otherwise
    """

    response = requests.head(link, headers=AUTH_HEADER).status_code
    return response == 200


def get_semesters_to_link():
    """
    Scrape a university page that has all the semesters that offered web-optioned courses. Tried to parse html
    without any libraries (how hard could it be ¯\_(ツ)_/¯ )

    :return: a dictionary where the keys are semesters and the values are links to the pages where it shows the
     courses that were weboptioned for that semester
    """

    # get web page
    webpage = requests.get(SEMESTERS_URL).text

    # parse webpage
    start_of_data_flag = 'UTSC Courses'
    end_of_data_flag = 'St. George Courses'

    # all the data we want is between start_of_data_flag and end_of_data_flag
    utsc_courses_tray = webpage[webpage.find(start_of_data_flag):
                                webpage.find(end_of_data_flag)]
    utsc_courses_tray = utsc_courses_tray.lower()

    # now for each semseter get the years
    seasons_to_years = {}
    for index in range(len(SEMESTERS)):
        start_index = utsc_courses_tray.find(SEMESTERS[index])
        end_index = -1 if (index == len(SEMESTERS) - 1) else utsc_courses_tray.find(SEMESTERS[index + 1])

        # get text between semesters
        seasons_to_years[SEMESTERS[index]] = utsc_courses_tray[start_index: end_index]

    # website divides semesters by seasons, so get each season to link
    seasons_to_links = {}
    for season in seasons_to_years:
        season_data = seasons_to_years[season]
        starting_index = 0
        semesters_links = []

        # delimiters
        start_of_semester_link = '<a href='
        end_of_semester_link = '</a>'

        # parse through html to get all the links for semesters
        while True:
            # get index of where data is
            starting_index = season_data.find(start_of_semester_link, starting_index + 1)
            ending_index = season_data.find(end_of_semester_link, starting_index + 1)

            if starting_index == -1 or ending_index == -1:
                break

            # minor clean up
            semester_link = season_data[starting_index: ending_index].replace(',', '')
            semesters_links.append(semester_link)

        seasons_to_links[season] = semesters_links

    # finally get semesters
    semesters_to_links = {}
    for season in seasons_to_links:
        links = seasons_to_links[season]
        for link in links:
            url = html.unescape(link[link.find("=\"") + 2: link.find("\">")])
            semesters_to_links[(link[-4:] + ' ' + season)] = url

    return semesters_to_links


def get_all_web_optioned_semesters():
    """
    get list semester of web-optioned semesters

    :return: list of semesters where courses were web-optioned
    """

    semesters_list = get_semesters_to_link().keys()
    list(semesters_list).sort()
    return semesters_list


def get_link_for_semester(year, season):
    """
    Get link for the page that holds data about courses that were web-optioned for a semester

    :param year: the year
    :param season: the season
    :return: link where all the data about courses for a particular semester is
    """

    return 'http://lecturecast.utsc.utoronto.ca/courses.php?year=' + year + '&session=' + SEASON_TO_CODE[season.lower()]


def get_link_for_course(course_code, year, season, lecture_number):
    """
    There's a particular pattern to the links for lectures

    :param course_code: the course code of lecture
    :param year: the year of lecture
    :param season: the season of lecture
    :param lecture_number: the lecture number of lecture
    :return: link for particular lecture
    """

    # ensure right types
    year = str(year)
    lecture_number = str(lecture_number)

    # add 0 in front lecture number if its one digit
    if len(lecture_number) == 1:
        lecture_number = '0' + lecture_number

    return 'https://lecturecast.utsc.utoronto.ca/lectures/' + year + '_' + season.capitalize() + '/' + course_code + \
           '/' + course_code + '_Lecture_' + lecture_number + '/' + course_code + '_Lecture_' + lecture_number + '.mp4'


def get_links_for_course(course, semester):
    """
    For a particular course that's been web-optioned find all the lecture links that work

    :param course: course that's web-optioned
    :param semester: the particular semester for the course
    :return: list of links for lectures of the particular course and semester
    """

    # TODO: should implement this more intelligently, i.e first check 1-13, if 13 exists then do 13-26 and on
    lecture_numbers = list(range(1, 14))  # maybe event 40 b/c some lectures happen 3 times a week

    possible_links = []
    year = semester.split(' ')[0]
    season = semester.split(' ')[1]

    # get all possible links
    for lecture_number in lecture_numbers:
        possible_links.append(get_link_for_course(course, year, season, lecture_number))

    working_links = []

    # TOTHINK: could do this part concurrently but might get flagged for DDOS, hmmm not sure
    for link in possible_links:
        if verify_working_link(link):
            working_links.append(link)

    return working_links


def get_course_data(course_array, semester):
    """
    Clean up course data

    :param course_array: has data about course
    :return: return cleaned up data in a dictionary
    """

    try:
        course_array.remove(' ')
    except ValueError:
        pass

    # handle some variation in course data
    offset = 1 if len(course_array) > 8 else 0

    # get the main data
    course = {
        'dept': course_array[1],
        'code': remove_non_alpha_num_char(course_array[3]),
        'lecture': course_array[4] if offset else '',
        'title': remove_non_alpha_num_char(course_array[5 + offset], True),
        'prof': (course_array[6 + offset]).strip(),
    }

    # add lecture links
    course['links'] = get_links_for_course(course['code'], semester) if semester else []

    return course


def get_courses_for_link(link, semester):
    """
    Scrape link that course data about course data for a particular semester. I don't want to parse another HTML file,
    so using BeautifulSoup to help me out.

    :param link: the link where the course data is
    :param semester: the semester for which we want course data
    :return: returns a list of course data (title, dept, prof, lectures) for all web-optioned courses in a semester
    """

    courses = []  # gonna be of type [{title: course_title, dept, prof}, {}, ...]
    try:
        # get html page
        page = requests.get(link).text

        # format html string
        html.unescape(page)

        # parse html
        soup = BeautifulSoup(page, 'html.parser')

        dirty_content = soup.find_all("tr", class_="style1")[0].find_all(string=True)

        # find indices of courses
        course_row_delimiter1 = '\xa0\n\t\t'
        course_row_delimiter2 = '\xa0\n'
        indices = [i for i, x in enumerate(dirty_content) if x == course_row_delimiter1 or x == course_row_delimiter2]

        start = 0

        # iterate through indices and take out particular courses
        # TODO: probably should implement this concurrently
        for i in range(len(indices)):
            end = indices[i]
            course_array = dirty_content[start: end]
            courses.append(get_course_data(course_array, semester))
            start = indices[i] + 1

    finally:
        return courses


def get_semesters_to_course():
    """
    Get semesters to course, bascially the culmination of everything

    :return: dictionary of semester to course data (where data has prof, dept, lectures, etc)
    """

    # get semesters_to_links
    semesters_to_links = get_semesters_to_link()

    semesters_to_courses = {}

    # for each link get the html and then get course data
    for semester in semesters_to_links:
        link = semesters_to_links[semester]
        semesters_to_courses[semester] = get_courses_for_link(link, semester)

    return semesters_to_courses
