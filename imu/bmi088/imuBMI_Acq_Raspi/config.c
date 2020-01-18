/*
 *  libConfig.cpp
 *
 *  General list structure
 *
 *  Author:  Bell
 
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License version 2 as
 *  published by the Free Software Foundation.
 */


#include "list.h"
#include "config.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct _tagConfigEntry {
	char name[MAX_LEN_ENTRY_NAME];
	int nameLen;
	char value[MAX_LEN_ENTRY_VALUE];
	int valueLen;
	List  listEntry;
} ConfigEntry, *pConfigEntry;

typedef struct _tagConfigGroup {
	char name[MAX_LEN_GROUP_NAME];
	List  listGroup;
	int   numEntry;
	ConfigEntry listConfigEntry;
} ConfigGroup, *pConfigGroup;

int setCurConfigGroup(char * grpName);
int addConfigGroup(char * grpName);
int parseConfigFile();

int initConfigs();
int freeConfigs();

static ConfigGroup configGroup;
static ConfigGroup *curConfigGroup=NULL;
static ConfigEntry *curConfigEntry=NULL;
static FILE * fp=NULL;
static char config_file[MAX_LEN_CFG]="";
static int bParsed=0;

int openConfigFile(char * fn)
{
	if (NULL == fn)
	{
		return -1;
	}

	if (fp != NULL)
	{
		//saveConfigFile();
		
		closeConfigFile();
	}

	//freeConfigs();
	
	memset(config_file, 0, MAX_LEN_CFG);

	int len = strlen(fn);

	if (len >= MAX_LEN_CFG) {
		return -2;
		//len = MAX_LENGTH_CFG - 1;
	}

	memcpy(config_file, fn, len);
	config_file[len] = '\0';	
	
	fp = fopen(config_file, "rt"); // Open it with read-only-text mode.
	if (NULL == fp)
	{
		fp = fopen(config_file, "wtc"); // Open it with read-only-text mode.
		if (NULL == fp) {
			return -3;
		} else {
			initConfigs();
			return 0;
		}
	}

	return parseConfigFile();
}

int setCurConfigGroup(char * grpName)
{
	List * pos_grp, * n_grp;
	//List * pos_entry, * n_entry;

	if (grpName==NULL)
		return -10;

	if (curConfigGroup!=NULL) {
		if (strcmp(curConfigGroup->name, grpName)==0) {
			return 0;
		}
	}
	
	if (!list_empty_careful(&configGroup.listGroup)) {
		list_for_each_safe(pos_grp, n_grp, &configGroup.listGroup) {
			ConfigGroup * grp;
			grp=list_entry(pos_grp, ConfigGroup, listGroup);
			//grp=container_of(pos_grp, ConfigGroup, listGroup);

			if (grp!=NULL) {
				if (strcmp(grp->name, grpName)==0) {
					curConfigGroup=grp;
					curConfigEntry=NULL;
					return 0;
				}
			}
		}
	}
	
	return -11;
}

int addConfigGroup(char * grpName)
{
	int len=strlen(grpName);
	if (len>=MAX_LEN_ENTRY_NAME)
		return -16;

	if (setCurConfigGroup(grpName)==0)
		return 0;	

	ConfigGroup * grp=(ConfigGroup *) malloc(sizeof(ConfigGroup));

	if (grp!=NULL) {
		grp->numEntry=0;
		memset(grp->name, 0, MAX_LEN_GROUP_NAME);
		memset(grp->listConfigEntry.name, 0, MAX_LEN_ENTRY_NAME);
		memset(grp->listConfigEntry.value, 0, MAX_LEN_ENTRY_VALUE);
		grp->listConfigEntry.valueLen=0;
		grp->listConfigEntry.nameLen=0;

		//INIT_LIST_HEAD(&configGroup.listGroup);
		INIT_LIST_HEAD(&grp->listConfigEntry.listEntry);

		memcpy(grp->name, grpName, len);
		list_add_tail(&grp->listGroup, &configGroup.listGroup);

		curConfigGroup=grp;
	}
	return 0;
}

int getConfigEntry(char * grpName, char * entryName, char * entryBuf, int entryBufSize)
{

	int len_grp, len_entry_name;
	if (grpName==NULL)
		return -20;
	
	len_grp=strlen(grpName);
	if (len_grp>=MAX_LEN_GROUP_NAME )
		return -21;

	if (entryName!=NULL && entryBuf!=NULL) {
		len_entry_name=strlen(entryName);

		if (len_entry_name>=MAX_LEN_ENTRY_NAME || entryBufSize>MAX_LEN_ENTRY_VALUE)
			return -22;
	} else {
		return -23;
	}

	if (setCurConfigGroup(grpName)==0) {
		List * pos_entry, * n_entry;

		if (curConfigGroup && !list_empty_careful(&curConfigGroup->listConfigEntry.listEntry)) {

			if (curConfigEntry!=NULL) {
				if (strcmp(curConfigEntry->name, entryName)==0) {
					
					if (curConfigEntry->valueLen<entryBufSize) {							
						//memcpy(entryBuf, curConfigEntry->value, curConfigEntry->valueLen);
						strcpy(entryBuf, curConfigEntry->value);
						
						return 0;
					} else {
					
						return -15;
					}
				}
			}
			
			list_for_each_safe(pos_entry, n_entry, &curConfigGroup->listConfigEntry.listEntry) {
				ConfigEntry* entry=list_entry(pos_entry, ConfigEntry, listEntry);
				if (entry) {
					if (strcmp(entry->name, entryName)==0) {
						curConfigEntry=entry;
						if (entry->valueLen<entryBufSize) {							
							//memcpy(entryBuf, entry->value, entry->valueLen);
							strcpy(entryBuf, entry->value);
							
							return 0;
						} else {
						
							return -14;
						}
					}
				}
				
			}

			return -13;
		}
		
	}
	
	return -12;
}

int setConfigEntry(char * grpName, char * entryName, char * entryBuf, int entryBufSize)
{
	int len_grp, len_entry_name;
	if (grpName==NULL)
		return -20;
	
	len_grp=strlen(grpName);
	if (len_grp>=MAX_LEN_GROUP_NAME )
		return -21;

	if (entryName!=NULL && entryBuf!=NULL) {
		len_entry_name=strlen(entryName);

		if (len_entry_name>=MAX_LEN_ENTRY_NAME || entryBufSize>MAX_LEN_ENTRY_VALUE)
			return -22;
	} else if (entryName==NULL && entryBuf==NULL){
		
	} else {
		return -23;
	}

	if (setCurConfigGroup(grpName)==0 || addConfigGroup(grpName)==0) {
		List * pos_entry, * n_entry;

		if (entryName==NULL && entryBuf==NULL)
			return 0;

		if (curConfigGroup) {

			if (curConfigEntry!=NULL) {
				if (strcmp(curConfigEntry->name, entryName)==0) {
					memset(curConfigEntry->value, 0, MAX_LEN_ENTRY_VALUE);
					memcpy(curConfigEntry->value, entryBuf, entryBufSize);
					curConfigEntry->valueLen=entryBufSize;
					
					return 0;
				}
			}
			
			list_for_each_safe(pos_entry, n_entry, &curConfigGroup->listConfigEntry.listEntry) {
				ConfigEntry* entry=list_entry(pos_entry, ConfigEntry, listEntry);
				if (entry) {
					if (strcmp(entry->name, entryName)==0) {
						memset(entry->value, 0, MAX_LEN_ENTRY_VALUE);
						memcpy(entry->value, entryBuf, entryBufSize);
						entry->valueLen=entryBufSize;

						curConfigEntry=entry;
						
						return 0;
					}
				}
				
			}

			ConfigEntry* entry=(ConfigEntry *) malloc(sizeof(ConfigEntry));

			if (entry!=NULL) {
				//grp->numEntry=0;
				//memset(grp->name, 0, MAX_LEN_GROUP_NAME);
				curConfigGroup->numEntry++;
				memset(entry->name, 0, MAX_LEN_ENTRY_NAME);
				memset(entry->value, 0, MAX_LEN_ENTRY_VALUE);
				entry->valueLen=entryBufSize;
				entry->nameLen=len_entry_name;

				memcpy(entry->name, entryName, len_entry_name);
				memcpy(entry->value, entryBuf, entryBufSize);
				list_add_tail(&entry->listEntry, &curConfigGroup->listConfigEntry.listEntry);

				//curConfigGroup=grp;

				return 0;
			}
			
			return -18;
		}
		
	}
	
	return -19;
}

char * getConfigLine(char *s, int size)
{
	char *chptr;
	
	chptr = fgets(s, size, fp);

	if (NULL == chptr)
	{
		return chptr;
	}
	else
	{
		// Del the CR and NL character at the end of line.
		int len = strlen(s);
		while (len > 0)
		{
			if (s[len-1] == 0x0A  ||  s[len-1] == 0x0D)
			{
				s[len-1] = '\0';
			}
			--len;
		}
		return s;
	}
}

int parseConfigFile()
{
	char opBuf[256];
	
	char    *ptr=NULL;
	char    buf[128];
	int     buflen=128;
	//int     stat=0;
	
	if (fp == NULL)
	{
		return -4;
	}

	memset(opBuf, '\0', 256);

	initConfigs();
	//bParsed=1;
	
	while (getConfigLine(buf, buflen) != NULL)
	{    
		ptr=buf;
		/*
		if (! strcmp(m_sField, ""))
			stat=1;
		else if (strstr(buf, m_sField))
		{
			stat=1;
			continue;
		}

		if (stat == 0)
			continue;
		*/
		 
		while (*ptr == '\t'  ||  *ptr == ' ')
			ptr++;	
		
		if ((*ptr == '\0')  ||
			(*ptr == '\n')  ||
			(*ptr == '\r')  ||
			(*ptr == ';')  ||
			(*ptr == '#'))
			continue;

		if (*ptr == '[') { // add a new group
			char *ptrEnd = strchr(ptr, ']');
			if ((ptrEnd-ptr)>1) {
				ptr++;
				while (*ptr == '\t'  ||  *ptr == ' ')
					ptr++;
				if (MAX_LEN_GROUP_NAME>(ptrEnd-ptr)) {
					ConfigGroup * grp=(ConfigGroup *) malloc(sizeof(ConfigGroup));

					if (grp!=NULL) {
						grp->numEntry=0;
						memset(grp->name, 0, MAX_LEN_GROUP_NAME);
						memset(grp->listConfigEntry.name, 0, MAX_LEN_ENTRY_NAME);
						memset(grp->listConfigEntry.value, 0, MAX_LEN_ENTRY_VALUE);
						grp->listConfigEntry.valueLen=0;
						grp->listConfigEntry.nameLen=0;

						//INIT_LIST_HEAD(&configGroup.listGroup);
						INIT_LIST_HEAD(&grp->listConfigEntry.listEntry);

						memcpy(grp->name, ptr, ptrEnd-ptr);
						list_add_tail(&grp->listGroup, &configGroup.listGroup);

						curConfigGroup=grp;
					}
				}
			}
			continue;
		} 

		/*
		if (strncmp(ptr, val, strlen(val)) != 0)
			continue;
		*/

		if (curConfigGroup==NULL)
			continue;			

		char * ptrValue = strchr(ptr, '=');
		if (ptrValue!=NULL) // add a new entry
		{
			while (*ptr == '\t'  ||  *ptr == ' ')
				++ptr;

			if ((*ptr == '\0')  ||
				(*ptr == '\n')  ||
				(*ptr == '\r')  ||
				(*ptr == ';')  ||
				(*ptr == '#'))
			{
				continue;
			}

			if ((ptrValue-ptr)<MAX_LEN_ENTRY_NAME) {
				int name_len=ptrValue-ptr;

				++ptrValue;
				while (*ptrValue == '\t'  ||  *ptrValue == ' ')
					++ptrValue;

				if ((*ptrValue == '\0')  ||
					(*ptrValue == '\n')  ||
					(*ptrValue == '\r')  ||
					(*ptrValue == ';')  ||
					(*ptrValue == '#'))
				{
					continue;
				}

				int len=0;

				if ((*ptrValue == '\"')  ||
					(*ptrValue == '\''))
				{
					char ch = *ptrValue;
					//int len = 0;

					++ptr;  // Ignore the start delimitation char
					do
					{
						if ((*ptrValue == '\0')  ||  (len >= MAX_LEN_ENTRY_VALUE))
						{   // Exception handle
							// opBuf[0] = '\0';
							// break;
							//xcpPtr->error(E_CONFIG_ERROR, SF_CFGBASE, "Missing delimitation char \' or \".");
							//return NULL;
							continue;
						}
						
						opBuf[len] = *ptrValue;
						++len;
						++ptrValue;
					} while (*ptrValue != ch);
					opBuf[len] = '\0';
				}
				else
				{
					//int len = 0;

					do
					{
						opBuf[len] = *ptrValue;
						++len;
						++ptrValue;
					} while ((*ptrValue != ' ')  &&
							(*ptrValue != '\0')  &&
							(*ptrValue != '\n')  &&
							(*ptrValue != '\r')  &&
							(*ptrValue != '\t')  &&
							(*ptrValue != ';')  &&
							(*ptrValue != '#') && len<MAX_LEN_ENTRY_VALUE);
					opBuf[len] = '\0';
				}

				//if (len)
				if (1) {
					ConfigEntry* entry=(ConfigEntry *) malloc(sizeof(ConfigEntry));

					if (entry!=NULL) {
						//grp->numEntry=0;
						//memset(grp->name, 0, MAX_LEN_GROUP_NAME);
						curConfigGroup->numEntry++;
						memset(entry->name, 0, MAX_LEN_ENTRY_NAME);
						memset(entry->value, 0, MAX_LEN_ENTRY_VALUE);
						entry->valueLen=len;
						entry->nameLen=name_len;

						memcpy(entry->name, ptr, name_len);
						memcpy(entry->value, ptrValue-len, len);
						list_add_tail(&entry->listEntry, &curConfigGroup->listConfigEntry.listEntry);

						//curConfigGroup=grp;
					}
				}
				
			} else {
				continue;
			}
			
			
		}
		// Exception handle
		// printf("[%s] Missing value\n",val);
		//xcpPtr->error(E_CONFIG_MISS, SF_CFGBASE, "The option missing value.");
		//return NULL;
	}

	return 0;
	//return NULL;
}

int dumpConfigs()
{
	List * pos_grp, * n_grp;
	List * pos_entry, * n_entry;
	
	if (!list_empty_careful(&configGroup.listGroup)) {
		list_for_each_safe(pos_grp, n_grp, &configGroup.listGroup) {
			ConfigGroup * grp;
			grp=list_entry(pos_grp, ConfigGroup, listGroup);
			//grp=container_of(pos_grp, ConfigGroup, listGroup);

			if (grp) {
				printf("[%s]\n", grp->name);
			}
			
			if (grp && !list_empty_careful(&grp->listConfigEntry.listEntry)) {
				list_for_each_safe(pos_entry, n_entry, &grp->listConfigEntry.listEntry) {
					ConfigEntry* entry=list_entry(pos_entry, ConfigEntry, listEntry);
					if (entry) {
						printf("%s=%s\n", entry->name, entry->value);
					}

					//grp->listConfigEntry
				}				
			}
		}
	}

	return 0;
}

int saveConfigFile()
{
	if (fp != NULL)
	{
		//saveConfigFile();
		fclose(fp);
		fp=NULL;
		//rewind(fp);
		//return E_SUCC;
	}

	fp = fopen(config_file, "wtc"); // Open it with read-only-text mode.
	if (NULL == fp)
	{
		return -3;
	}

	List * pos_grp, * n_grp;
	List * pos_entry, * n_entry;

	fprintf(fp, "#%s\n\n", config_file);
	fflush(fp);
	
	if (!list_empty_careful(&configGroup.listGroup)) {
		list_for_each_safe(pos_grp, n_grp, &configGroup.listGroup) {
			ConfigGroup * grp;
			grp=list_entry(pos_grp, ConfigGroup, listGroup);
			//grp=container_of(pos_grp, ConfigGroup, listGroup);

			if (grp) {
				fprintf(fp, "\n[%s]\n", grp->name);
				fflush(fp);
			}
			
			if (grp && !list_empty_careful(&grp->listConfigEntry.listEntry)) {
				list_for_each_safe(pos_entry, n_entry, &grp->listConfigEntry.listEntry) {
					ConfigEntry* entry=list_entry(pos_entry, ConfigEntry, listEntry);
					if (entry) {
						fprintf(fp, "%s=%s\n", entry->name, entry->value);
						fflush(fp);
					}

					//grp->listConfigEntry
				}				
			}
		}
	}

	fflush(fp);

	if (fp != NULL)
	{
		//saveConfigFile();
		fclose(fp);
		fp=NULL;
		//rewind(fp);
		//return E_SUCC;
	}
	
	return 0;
}

int initConfigs()
{
	configGroup.numEntry=0;
	memset(configGroup.name, 0, MAX_LEN_GROUP_NAME);
	memset(configGroup.listConfigEntry.name, 0, MAX_LEN_ENTRY_NAME);
	memset(configGroup.listConfigEntry.value, 0, MAX_LEN_ENTRY_VALUE);
	configGroup.listConfigEntry.valueLen=0;
	configGroup.listConfigEntry.nameLen=0;

	curConfigGroup=NULL;
	curConfigEntry=NULL;
	
	INIT_LIST_HEAD(&configGroup.listGroup);
	INIT_LIST_HEAD(&configGroup.listConfigEntry.listEntry);

	bParsed=1;

	return 0;
}

int freeConfigs()
{
	List * pos_grp, * n_grp;
	List * pos_entry, * n_entry;
	
	if (!list_empty_careful(&configGroup.listGroup)) {
		list_for_each_safe(pos_grp, n_grp, &configGroup.listGroup) {
			ConfigGroup * grp=list_entry(pos_grp, ConfigGroup, listGroup);
			if (grp && !list_empty_careful(&grp->listConfigEntry.listEntry)) {
				list_for_each_safe(pos_entry, n_entry, &grp->listConfigEntry.listEntry) {
					ConfigEntry* entry=list_entry(pos_entry, ConfigEntry, listEntry);
					if (entry) {
						free(entry);

						grp->numEntry--;
					}

					//grp->listConfigEntry
				}

				if (grp) {
					free(grp);
				}
			}
		}
	}

	curConfigGroup=NULL;
	curConfigEntry=NULL;

	//initConfigs();

	return 0;
}

int closeConfigFile()
{
	if (fp != NULL)
	{
		//saveConfigFile();
		fclose(fp);
		fp=NULL;
		//rewind(fp);
		//return E_SUCC;
	}

	if(bParsed) {
		freeConfigs();
		bParsed=0;
	}

	return 0;
}



