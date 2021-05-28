#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Apple Health XML to CSV
==============================
:File: convert.py
:Description: Convert Apple Health "export.xml" file into a csv
:Version: 0.0.1
:Created: 2019-10-04
:Authors: Jason Meno (jam)
:Dependencies: An export.xml file from Apple Health
:License: BSD-2-Clause
"""

# %% Imports
import pandas as pd
import xml.etree.ElementTree as ET
import datetime as dt


# %% Function Definitions
def pre_process():
    """Pre-processes the XML file by replacing specific bits that would
    normally result in a ParseError
    """

    print('Pre-processing...', end='')
    with open('export.xml') as f:
        newText = f.read().replace('\x0b', '')

    with open('processed_export.xml', 'w') as f:
        f.write(newText)

    print('done!')

    return


def convert_xml():
    """Loops through the element tree, retrieving all objects, and then
    combining them together into a dataframe
    """

    print('Converting XML File...', end='')
    etree = ET.parse('processed_export.xml')

    attribute_list = []

    for child in etree.getroot():
        child_attrib = child.attrib
        for metadata_entry in list(child):
            metadata_values = list(metadata_entry.attrib.values())
            if len(metadata_values) == 2:
                metadata_dict = {metadata_values[0]: metadata_values[1]}
                child_attrib.update(metadata_dict)

        attribute_list.append(child_attrib)

    health_df = pd.DataFrame(attribute_list)

    # Every health data type and some columns have a long identifier
    # Removing these for readability
    health_df.type = health_df.type.str.replace('HKQuantityTypeIdentifier', '')
    health_df.type = health_df.type.str.replace('HKCategoryTypeIdentifier', '')
    health_df.columns = \
        health_df.columns.str.replace('HKCharacteristicTypeIdentifier', '')

    # Reorder some of the columns for easier visual data review
    original_cols = list(health_df)
    shifted_cols = ['type',
                    'sourceName',
                    'value',
                    'unit',
                    'startDate',
                    'endDate',
                    'creationDate']

    # Add loop specific column ordering if metadata entries exist
    if 'com.loopkit.InsulinKit.MetadataKeyProgrammedTempBasalRate' in original_cols:
        shifted_cols.append('com.loopkit.InsulinKit.MetadataKeyProgrammedTempBasalRate')

    if 'com.loopkit.InsulinKit.MetadataKeyScheduledBasalRate' in original_cols:
        shifted_cols.append('com.loopkit.InsulinKit.MetadataKeyScheduledBasalRate')

    if 'com.loudnate.CarbKit.HKMetadataKey.AbsorptionTimeMinutes' in original_cols:
        shifted_cols.append('com.loudnate.CarbKit.HKMetadataKey.AbsorptionTimeMinutes')

    remaining_cols = list(set(original_cols) - set(shifted_cols))
    reordered_cols = shifted_cols + remaining_cols
    health_df = health_df.reindex(labels=reordered_cols, axis='columns')

    # Sort by newest data first
    health_df.sort_values(by='startDate', ascending=False, inplace=True)

    print('done!')

    return health_df


# New function to group and sum the data to create a shortened table
def group_and_sum(df):
    """Groups and sums the data to create a shorter and more readable table"""

    df = df.drop(['startDate', 'endDate', 'device', 'FitzpatrickSkinType',
                  'sourceVersion', 'HKTimeZone', 'CardioFitnessMedicationsUse',
                  'BloodType', 'DateOfBirth', 'BiologicalSex',
                  'HKMetadataKeyDevicePlacementSide'], axis=1)

    df['creationDate'] = df['creationDate'].astype(str)
    df['date'] = pd.to_datetime(df['creationDate'], infer_datetime_format=True).dt.date

    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Group and sum rows where 'type', 'sourceName', 'unit' and 'date' match
    health_df_grouped = df.groupby(['type',
                                    'sourceName',
                                    'unit',
                                    'date']).agg({'value': 'sum'}).reset_index()

    health_df_grouped.sort_values(by=['date', 'type'], ascending=True, inplace=True)

    return health_df_grouped


# New function to transpose the shortened table to have only one row per day with multiple columns
def transpose(df):
    """Transposes the shortened table to have one row per day"""

    tr_table = []

    for index, row in df.iterrows():

        tr_table.append({'date': row['date'],
                         '{type}({unit})'.format(type = row['type'], unit = row['unit']): row['value'],
                         'sourceName': row['sourceName'],
                         })

    df1 = pd.DataFrame(tr_table)

    df1 = df1.drop(['HeadphoneAudioExposure(dBASPL)', 'WalkingAsymmetryPercentage(%)',
                    'WalkingDoubleSupportPercentage(%)', 'WalkingSpeed(km/hr)',
                    'WalkingStepLength(cm)', 'BodyMass(kg)', 'Height(cm)'], axis=1)

    # Group and sum rows where 'date' and 'sourceName' match
    health_df_transposed = df1.groupby(['date',
                                        'sourceName'
                                        ]).agg('sum').reset_index()

    return health_df_transposed


# Added version name, as we now save two different versions of the dataset
def save_to_csv(df, version_name):
    print("Saving CSV file...", end="")
    today = dt.datetime.now().strftime('%Y-%m-%d')
    df.to_csv("apple_health_export_" + version_name + today + ".csv", index=False)
    print("done!")

    return


def main():
    pre_process()

    health_df = convert_xml()
    health_df_grouped = group_and_sum(health_df)
    health_df_transposed = transpose(health_df_grouped)

    save_to_csv(health_df, 'original_')
    save_to_csv(health_df_grouped, 'grouped_')
    save_to_csv(health_df_transposed, 'transposed_')

    return


# %%
if __name__ == '__main__':
    main()
