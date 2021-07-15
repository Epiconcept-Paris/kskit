import random
import string
import time
from datetime import datetime
import os
import pydicom
import numpy as np
from dpiste import utils
from dpiste.dicom2png import dicom2narray, narray2dicom
from PIL import Image, ImageFont, ImageDraw
from .p08_mammogram_deidentification import *

PATH_DCM = '/home/williammadie/images/test_mix/dicom'
PATH_PNG = '/home/williammadie/images/test_mix/png'
PATH_FONTS = '/home/williammadie/images/fonts'

"""

This module aims at evaluating the OCR package abilities. 
It generates and adds random texts to test images and then treats them with 
the OCR module.

"""

def p08_000_test_OCR(font, size, blur, repetition):    
    start_time = time.time()
    #Default values
    utils.get_home('data', 'input', 'hdh','')
    utils.get_home('data','output','hdh','')
    utils.get_home('data','transform','hdh','')
    indir = os.environ.get('DP_HOME') + '/data/input/hdh'
    outdir = os.environ.get('DP_HOME') + '/data/output/hdh'
    outdir_intermediate = os.environ.get('DP_HOME') + '/data/transform/hdh'

    if font is None:
        font = [PATH_FONTS + '/FreeMono.ttf']
    if size is None:
        size = [2]
    if blur is None:
        blur = [0]
    if repetition is None:
        repetition = 1

    check_resources(font, size, blur)

    sum_ocr_recognized_words, sum_total_words, nb_images_tested = 0, 0, 1
    tp, tn, fp, fn = 0, 0, 0, 0
    list_dicom, list_chosen = sorted(os.listdir(indir)), []
    result = ""

    #Tests for false positives
    (nb_images_tested, list_chosen, summary, fp, tn) = search_false_positives(
        indir, list_dicom, list_chosen, outdir_intermediate, repetition, nb_images_tested, fp, tn)
    
    #Tests for criteria FONT, SIZE & BLUR
    nb_images_total = len(font)*len(size)*len(blur)*3 + 3
    summary += "\n\n\nTested with several FONT SIZE & BLUR parameters x" + \
    str(nb_images_total - 3) + "\n\n\n"
    for index_font in range(len(font)):
        for index_size in range(len(size)):
            for index_blur in range(len(blur)):
                for r in range(repetition):
                    (pixels, ds, dicom, file_path, list_chosen) = get_random_dicom_ds_array(
                        list_dicom, indir, list_chosen
                        )
                    
                    if pixels.size < 100000:
                        test_words = generate_random_words(random.randint(1,1), 5)
                    elif size[index_size] > 3:
                        test_words = generate_random_words(random.randint(1,5), 5)
                    else:
                        test_words = generate_random_words(random.randint(1,10), 10)

                    (pixels, words_array, test_words) = add_words_on_image(
                        pixels, test_words, size[index_size], 
                        font=font[index_font], blur=blur[index_blur]
                        )

                    img = Image.fromarray(pixels)
                    img.save(outdir + '/' + os.path.basename(dicom) + ".png")

                    ocr_data = p08_002_get_text_areas(pixels)
            
                    (ocr_recognized_words, total_words) = compare_ocr_data_and_reality(
                        test_words, words_array, ocr_data
                        )

                    #Test numbers :
                    sum_ocr_recognized_words += ocr_recognized_words
                    sum_total_words += total_words

                    #Calculate test model values
                    (tp, tn, fn) = calculate_test_values(
                        total_words, ocr_recognized_words, tp, tn, fn
                        )        
                    result = save_test_information(
                        nb_images_tested, nb_images_total, sum_ocr_recognized_words, sum_total_words, 
                        ocr_recognized_words, total_words, tp, tn, fp, fn, outdir_intermediate, file_path, result
                        )
                    save_dicom_info(
                        outdir_intermediate + '/' + os.path.basename(dicom) + ".txt", 
                        file_path, ds, ocr_data, test_words, total_words)
                    
                    summary += "\n" + file_path + "\n↪parameters : F = " \
                         + str(os.path.basename(font[index_font])) + " | B = " \
                             + str(blur[index_blur]) + " | S = " + str(size[index_size])
                    nb_images_tested += 1
    
    time_taken = time.time() - start_time
    with open(outdir_intermediate + '/test_summary.log', 'w') as f:
        f.write(
          str(round(time_taken/60)) + " minutes taken to process all images.\n" + \
          summary)
            
    #pixels = hide_text(pixels, ocr_data)
    #narray2dicom(pixels, dicom[1], (pathPNG + "/dicom/de_identified" + str(count) + ".dcm"))



def search_false_positives(indir, list_dicom, list_chosen, outdir_intermediate, repetition, nb_images_tested, fp, tn):
    summary = "\nF stands for the FONT path" + \
        "\nB stands for the BLUR strength" + \
            "\nS stands for the text SIZE"
    summary += "\n\n\nTested for detecting possible false positives x" + str(repetition) + "\n\n\n"
    for i in range(repetition):
        (pixels, ds, dicom, file_path, list_chosen) = get_random_dicom_ds_array(list_dicom, indir, list_chosen)
        ocr_data = p08_002_get_text_areas(pixels)
        if is_there_ghost_words(ocr_data):
            fp += 1
        else:
            tn += 1
        save_dicom_info(
            outdir_intermediate + '/' + os.path.basename(dicom) + ".txt", 
            file_path, ds, ocr_data, [], 0
            )
        summary += "\n" + file_path + "\n↪parameters : F = - | B = - | S = -"
        nb_images_tested += 1

    return (nb_images_tested, list_chosen, summary, fp, tn)



def check_resources(font, size, blur):
    """Checks if all font resources are existing and correct"""
    for f in font:
        if not os.path.isfile(f):
            raise TypeError("Font " + f + " does not exist. Please check spelling.") 

    if max(size) > 5 or min(size) < 1:
        raise ValueError("Possible text sizes are [1, 2, 3, 4, 5]")
    
    if max(blur) > 10 or min(blur) < 0:
        raise ValueError("Possible blur strengths are [0..10]")



def get_random_dicom_ds_array(list_dicom, indir, list_chosen):
    """Returns the dataset and the array of a random dicom file in the folder"""
    while True:
        dicom = list_dicom[random.randint(0, len(list_dicom)-1)]
        if dicom not in list_chosen:
            list_chosen.append(dicom)
            break
        else:
            if len(list_chosen) == len(list_dicom):
                break

    file_path = indir + '/' + dicom
    (pixels, ds) = dicom2narray(file_path)
    return (pixels, ds, dicom, file_path, list_chosen)



def save_dicom_info(output_ds, file_path, ds, ocr_data, test_words, total_words):
    """Write the dataset of the image"""
    with open(output_ds,'a') as f:
        f.write(
            datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
                ) + '\n' + file_path + '\n' + str(ds) + "\nRecognized words :\n")
        ocr_words = []
        for found in ocr_data:
            if ' ' in found[1]:
                new_tuple = (found[0], found[1].replace(' ',''), found[2])
                ocr_data.remove(found)
                ocr_data.append(new_tuple)
            ocr_words.append(found[1])
        for found in sorted(ocr_words):
            f.write(found.lower() + " |")
        f.write("\nReal words :\n")
        if total_words == len(test_words):
            for word in sorted(test_words):
                f.write(word + " |")


def summarize_dcm_info(pixels, file, count):
    """
    Debug function which prints useful information of the narray (@param pixels)
    """
    strObtenue = """
Nbre de dimensions : {0},
Taille dim1, dim2 : {1},
Nbre total d'éléments : {2},
Taille dimension 1 : {3},
(vMin, vMax) contenu dans une cellule : {4},
MONOCHROME : {5}

==================================================
        """.format(
            pixels.ndim,
            pixels.shape,
            pixels.size,
            len(pixels),
            (pixels.amin(), pixels.amax()),
            pydicom.read_file(PATH_DCM + "/" + file).PhotometricInterpretation
        )
    print("==================================================\n")
    print("Image n°" + str(count) + " : " + file + "\n" + strObtenue )



def generate_random_words(nb_words, nb_character_max, nb_character_min = 3):
    """
    Generates 'nb_words' random words composed from 1 to 'nb_character_max' ASCII characters.
    """
    words = []

    for i in range(nb_words):
        word = string.ascii_letters
        word = ''.join(
            random.choice(word) for i in range(
                random.randint(nb_character_min,nb_character_max)
                )
            )
        words.append(word)
    
    return words
        



def add_words_on_image(pixels, words, text_size, font, color = 255, blur = 0):
    """Writes text on each picture located in the folder path."""
    nb_rows = 15
    
    #No words = empty array
    if len(words) == 0:
        words_array = words_array = np.full((nb_rows, nb_rows), 0)
        return (pixels, words_array, words)

    #Create a pillow image from the numpy array
    pixels = pixels/255
    im = Image.fromarray(np.uint8((pixels)*255))
    
    #Auto-scale the size of the text according to the image width
    if text_size == 'auto':
        text_size = auto_scale_font_size(pixels, font, 1)
        print(text_size)
    else:
        text_size = auto_scale_font_size(pixels, font, text_size)
    img_font = ImageFont.truetype(font, text_size)
    
    #Intialize the information for 'words_array' 
    image_width, image_height = pixels.shape[1], pixels.shape[0]
    length_cell, height_cell = image_width/nb_rows, image_height/nb_rows

    #Creates an array of 'nb_rows x nb_rows' filled with 0.
    words_array = words_array = np.full((nb_rows, nb_rows), 0)

    count = 0
    for word in words:
        #While the cell is occupied by a word or too luminous, we keep looking for anoter free cell
        random_cell, x_cell, y_cell, nb_tries = -1, -1, -1, 0
        is_null = False
        while not is_null:
            random_cell = random.randint(0, words_array.size)
            
            #Gets the x and the y of the random_cell
            num_cell = 0
            for x in range(nb_rows):
                for y in range(nb_rows):
                    if num_cell == random_cell:
                        x_cell, y_cell = x, y
                    num_cell += 1

            #The array memorizes the position of the word in the list 'words'
            if words_array[x_cell][y_cell] == 0 and x_cell < nb_rows-2 \
                and is_the_background_black_enough(x_cell, y_cell, length_cell, height_cell, im):
                
                occupied = False
                for cell in range(5, 0, -1):
                    if x_cell+cell >= len(words_array):
                        occupied = True
                        break
                    if words_array[x_cell+cell][y_cell] != 0:
                        occupied = True
                        break
                
                if not occupied:
                    for cell in range(5, 0, -1):
                        words_array[x_cell+cell][y_cell] = count+1
                    is_null = True
                    nb_tries = 0
            nb_tries += 1

            #If the number of tries exceeds the limit, we remove the word from the list
            if nb_tries >= 120:
                break
           
        if nb_tries < 120:
            #x and y coordinates on the image
            x_cell = x_cell * length_cell
            y_cell = y_cell * height_cell
            
            #Position of the word on the image
            draw = ImageDraw.Draw(im)
            
            #Adds the text on the pillow image
            draw.text((x_cell, y_cell), words[count], fill=color, font=img_font)
            
            #Blur effect
            if blur != 0:
                im = blur_it(im, blur, x_cell, y_cell, length_cell, height_cell)
            
            count += 1
            del draw

    #Converts the pillow image into a numpy array and returns it
    return (np.asarray(im), words_array, words)




def auto_scale_font_size(pixels, font, rescale_size):
    """
    Rescale the text depending on the the width of an image.
    Parameters : pixels (narray of the image)
    words : a list of the words to add on the picture
    font : the path of the font to use 
    rescale_size : from 1 to 5 (1 is the smaller size / 5 is the bigger size)
    """
    text_size = 1
    img_font = ImageFont.truetype(font, text_size)
    
    rescale_sizes = [0.1, 0.2, 0.3, 0.4, 0.5]
    img_fraction = rescale_sizes[rescale_size-1]
    while img_font.getsize("1234567890")[0] < img_fraction*pixels.shape[1]:
        text_size += 1
        img_font = ImageFont.truetype(font, text_size)
    text_size -= 1

    if text_size < 18:
        text_size = 18

    return text_size



def blur_it(image, blur, x, y, length_cell, height_cell):
    """
    Blur a specified rectangle area on a picture. Parameters :
    Image to blur, strength of the blur effect, x and y of the top-left 
    corner of the area,
    length_cell and height_cell : length and height of the rectangle.  
    """
    box = (int(x), int(y), int(x + 4 * length_cell), int(y + height_cell))            
    cut = image.crop(box)
    for i in range(blur):
        cut = cut.filter(ImageFilter.BLUR)
    image.paste(cut, box)

    return image



def is_the_background_black_enough(x_cell, y_cell, length_cell, height_cell, im):
    """
    Checks if the area chosen for the text is black enough to set white text on it.
    returns True if the area is correct. Returns False in other cases.
    """
    
    if x_cell == -1 and y_cell == -1:
        return False

    x_im = x_cell * length_cell
    y_im = y_cell * height_cell

    box = (x_im, y_im, x_im+length_cell, y_im+height_cell)
    cut = im.crop(box)

    area_array = np.asarray(cut)

    avg = 0
    for x in range(len(area_array)):
        for y in range(len(area_array[x])):
            avg += area_array[x][y]
    avg /= area_array.size

    return avg < 20



def levenshtein_distance(word_1, word_2):
    """
    Calculates the levenshtein distance (= the number of letters to add/
    substitute/interchange in order to pass from word_1 to word_2)
    """
    array = [[0 for i in range(len(word_2)+1)] for y in range(len(word_1)+1)]

    for i in range(len(word_1)+1):
        array[i][0] = i
    for j in range(len(word_2)+1):
        array[0][j] = j
    
    for i in range(1, len(word_1)+1):
        for j in range(1, len(word_2)+1):
            cost = 0 if word_1[i-1] == word_2[j-1] else 1
            array[i][j] = min(
                array[i-1][j] + 1,
                array[i][j-1] + 1,
                array[i-1][j-1] + cost
                )

    return array[len(word_1)][len(word_2)]     
       
"""
TODO : Include this test in the right place
def test_levenshtein_distance():
    assert OCR_test_series.levenshtein_distance("chien","niche") == 4
    assert OCR_test_series.levenshtein_distance("javawasneat","scalaisgreat") == 7
    assert OCR_test_series.levenshtein_distance("forward","drawrof") == 6
    assert OCR_test_series.levenshtein_distance("distance","eistancd") == 2
    assert OCR_test_series.levenshtein_distance("sturgeon","urgently") == 6
    assert OCR_test_series.levenshtein_distance("difference","distance") == 5
    assert OCR_test_series.levenshtein_distance("example","samples") == 3
    assert OCR_test_series.levenshtein_distance("bsfhebfkrn","bsthebtkrn") == 2
    assert OCR_test_series.levenshtein_distance("cie","cle") == 1
"""

def is_there_ghost_words(ocr_data):
    """
    Calculates the amount of ghost words on the image.
    Ghost words refers to words or letters recognized by the OCR module 
    where there is actually no word or letter. 
    """
    for found in ocr_data:
            return True



def calculate_test_values(
    total_words, ocr_recognized_words, 
    tp, tn, fn
    ): 
    """
    Calculates the model test values :
    TP : True Positive  (There are words and every word has been recognized)
    TN : True Negative  (There is no word and no word has been recognized)
    FP : False Positive (There is no word but a word (or more) has been recognized)
    FN : False Negative (There are words and NOT every word has been recognized)
    """
    
    if total_words == 0:
        tn += 1
    else:
        if ocr_recognized_words/total_words == 1:
            tp += 1
        else:
            fn += 1
    return (tp, tn, fn)



def compare_ocr_data_and_reality(test_words, words_array, ocr_data):
    """
    Calculates the amount of recognized words compared to the total of words on the image
    """
    indices_words_reality = []
    ocr_recognized_words = 0

    print(test_words)

    for found in ocr_data:
        if ' ' in found[1]:
            print(found[1])
            new_tuple = (found[0], found[1].replace(' ',''), found[2])
            ocr_data.remove(found)
            ocr_data.append(new_tuple)
        print(found[1])
    #If the array contains an indice different than 0, we add it to a list.
    for x in range(len(words_array)):
        for y in range(len(words_array[x])):
            if words_array[x][y] != 0:
                indices_words_reality.append(words_array[x][y])
    
    #Remove duplicates
    indices_words_reality = list(dict.fromkeys(indices_words_reality))

    #Get the number of words present on the picture
    total_words = 0
    for word in indices_words_reality:
        total_words += 1

    #Set each word to lower case
    for word in range(len(test_words)):
        test_words[word] = test_words[word].lower()

    #Get the number of words recognized 
    unrecognized_words = []
    for found in ocr_data:
        if found[1].lower() in test_words:
            ocr_recognized_words += 1
            test_words.remove(found[1].lower())
        #The OCR module has a tendency to confuse i and l or o and q. We help it because it does not matter for our work. 
        else:
            for word_pos in range(len(test_words)):
                difference = levenshtein_distance(found[1].lower(), test_words[word_pos])
                if (difference <= 3 and min(len(found[1]), len(test_words[word_pos])) > 3) or \
                    (difference <= 1 and min(len(found[1]), len(test_words[word_pos])) <= 3) :
                    print(found[1].lower(), "&&", test_words[word_pos], 
                    "==", difference)
                    ocr_recognized_words += 1
                    test_words.remove(test_words[word_pos])
                    break
                elif word_pos == len(test_words)-1:
                    if found[1] not in unrecognized_words:
                        unrecognized_words.append(found[1])

    print("Unrecognized :", unrecognized_words)
    if len(unrecognized_words) != 0:
        sum_words = ""
        for word in unrecognized_words:
            sum_words += word
            print(sum_words)
        for word in test_words:
            if sum_words.find(word) != -1:
                ocr_recognized_words += 1
                test_words.remove(word)
                print(word, "is contained in", sum_words)

    return (ocr_recognized_words, total_words)



def save_test_information(nb_images_tested, nb_images_total, sum_ocr_recognized_words, sum_total_words, 
ocr_recognized_words, total_words, tp, tn, fp, fn, outdir_intermediate, file_path, result):
    """
    Save the test information in a .txt file. 
    It contains main values linked to the past test.
    """
    #Counter Division by zero
    if tp != 0 or fp != 0:
        accuracy = (tp + tn) / (tp + tn + fn + fp)*100
        precision = tp / (tp+fp)
        recall = tp / (tp+fn)
        if precision == 0 and recall == 0:
            f1_score = -1
        else:
            f1_score = (2 * precision * recall) / (precision + recall)
    else:
        accuracy, precision, recall, f1_score = -1, -1, -1, -1

    if total_words != 0:
        percentage_recognized = (ocr_recognized_words/total_words)*100
    else:
        percentage_recognized = 100

    if sum_total_words != 0:
        percentage_total_recognized = (sum_ocr_recognized_words/sum_total_words)*100
    else:
        percentage_total_recognized = 100

    accuracy, precision = round(accuracy, 1), round(precision, 1)
    recall, f1_score = round(recall, 1), round(f1_score, 1)
    hour = datetime.now().strftime("%H:%M:%S")
    prompt = """
\n
===========================================================================
Image : {file_path}
Image tested at : {hour}
Amount of images tested: {nb_images_tested}/{nb_images_total}
TOTAL: {ocr_recognized_words}/{total_words} words recognized (last image) ({percentage_recognized}%)
GRAND TOTAL: {sum_ocr_recognized_words}/{sum_total_words} words recognized ({percentage_total_recognized}%)
True Positive (totally recognized images): {tp}
False Negative (NOT totally recognized images): {fn}
False Positive (Images with ghost words): {fp}
True Negative (Images with NO ghost words): {tn}
Precision: {precision}
Recall: {recall}
F1_Score: {f1_score}
Accuracy: {accuracy} % 
===========================================================================
\n
    """.format(
        file_path = file_path, hour = hour, nb_images_tested = nb_images_tested,
        nb_images_total = nb_images_total, ocr_recognized_words = ocr_recognized_words,
        total_words = total_words, percentage_recognized = percentage_recognized,
        percentage_total_recognized = percentage_total_recognized,
        sum_ocr_recognized_words = sum_ocr_recognized_words, 
        sum_total_words = sum_total_words, tp = tp, fn = fn, fp = fp, tn = tn, 
        precision = precision, recall = recall, f1_score = f1_score, accuracy = accuracy)
    print(prompt)
    result += prompt

    if nb_images_tested == nb_images_total:
        if outdir_intermediate.endswith('/'):
            file_path = outdir_intermediate + "test_info.log" 
        else:
            file_path = outdir_intermediate + "/test_info.log"
            
        with open(file_path, 'a') as f:
            f.write(result)
    else:
        return result



if __name__ == '__main__':  
    p08_000_test_OCR(     
        [PATH_FONTS+"/FreeSansBoldOblique.ttf", PATH_FONTS+"/P052-Roman.otf", 
        PATH_FONTS+"/NimbusRoman-Regular.otf", PATH_FONTS+"/FreeSerif.ttf"], 
        [1, 2, 5], [0], 3
        )