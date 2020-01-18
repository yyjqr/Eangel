#ifndef __DEBUG_H__
#define	__DEBUG_H__

#define STR_OK          "[\x1b[1;32m OK \x1b[0m]"
#define STR_FAIL        "[\x1b[1;31mFAIL\x1b[0m]"


#ifdef __cplusplus
extern "C" {
#endif

// #define DEBUG
#define PARAMETER

  enum debug_msg_level {
    MSG_LEVEL_OFF     = 0,
    MSG_LEVEL_ERROR,
    MSG_LEVEL_WARNING,
    MSG_LEVEL_INFO,
    MSG_LEVEL_VERBOSE,
    MSG_LEVEL_DEBUG,
    MSG_LEVEL_MAX
  };

#ifdef PARAMETER
extern int trace_level;
#undef  ac_traces
#define ac_traces(level, msg...) do {					\
    if((level) >= trace_level) {					\
      printf("\033[0;31m[DEBUG] file:%s func:%s line:%d\033[0;39m\n",__FILE__, __FUNCTION__, __LINE__); \
      printf(msg);							\
      printf("\n");							\
    }									\
  }while(0)
#else
#define TRACE_LEVEL	MSG_LEVEL_INFO
#undef  ac_traces
#define ac_traces(level, msg...) do {					\
    if((level) >= TRACE_LEVEL) {					\
      printf("\033[0;31m[DEBUG] file:%s func:%s line:%d\033[0;39m\n",__FILE__, __FUNCTION__, __LINE__); \
      printf(msg);							\
      printf("\n");							\
    }									\
  }while(0)
#endif

#define pr_err(format, ...)  fprintf(stderr, format, ##__VA_ARGS__)
#define pr_info(format, ...) fprintf(stdout, format, ##__VA_ARGS__)

#ifdef __cplusplus
}
#endif

#endif /* __DEBUG_H__ */
