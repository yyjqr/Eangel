/*
 *  libConfig.h
 *
 *  General list structure
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License version 2 as
 *  published by the Free Software Foundation.
 */

#ifndef _LIBCONFIG_HEADER
#define _LIBCONFIG_HEADER

#include "list.h"

#define MAX_LEN_CFG 128
#define MAX_LEN_GROUP_NAME 64
#define MAX_LEN_ENTRY_NAME 64
#define MAX_LEN_ENTRY_VALUE 128


int openConfigFile(char * confFileName);
int getConfigEntry(char * grpName, char * entryName, char * entryBuf, int entryBufSize);
int setConfigEntry(char * grpName, char * entryName, char * entryBuf, int entryBufSize);
int saveConfigFile();
int closeConfigFile();

int dumpConfigs();

#endif

