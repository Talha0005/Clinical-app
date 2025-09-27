import inspect
import assemblyai as aai
print('version', getattr(aai, '__version__', 'unknown'))
RT = getattr(aai, 'RealtimeTranscriber', None)
print('has RT:', bool(RT))
if RT:
    print('RT __init__:', inspect.signature(RT.__init__))
    try:
        inst = RT()
        print('instantiated no-args OK')
    except Exception as e:
        print('no-args init failed:', type(e).__name__, e)
    for name in ['connect','start','open','begin','stream','send_audio','send','send_pcm','close']:
        try:
            has = hasattr(RT, name) or ('inst' in locals() and hasattr(inst, name))
            print(f'{name}:', has)
            if has:
                obj = getattr(inst if 'inst' in locals() and hasattr(inst, name) else RT, name)
                print(f'  sig {name}:', inspect.signature(obj))
        except Exception as e:
            print(f'  sig {name} err:', e)
PT = getattr(aai, 'RealtimePartialTranscript', None)
FT = getattr(aai, 'RealtimeFinalTranscript', None)
Err = getattr(aai, 'RealtimeError', None)
print('has types:', bool(PT), bool(FT), bool(Err))
