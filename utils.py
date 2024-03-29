import torch
from torch.utils.tensorboard import SummaryWriter
import os, json
from model import Encoder, cp_2_k_mask
from tensorboard import program

optim = torch.optim

class TensorboardLogger:
    def __init__(self, args):
        #Logger
        # self.global_step = 0
        self.logger = {}

        # Make Path
        # log_path = os.path.join(root, strftime("%a%d%b%Y%H%M%S", gmtime()))
        # os.makedirs(log_path)
        self.writer = SummaryWriter(args['LOG'])

        # Make a copy of config file
        with open(os.path.join(args['LOG'], 'config.json'), "w") as outfile:
            json.dump(args, outfile)

    def update(self, key, value):
        try:
            self.logger[key]['step'] += 1
            self.logger[key]['value'] = value
        except:
            self.logger[key] = {'value': value, 'step': 0}


        # self.global_step += 1
        for k, v in self.logger.items():
            self.writer.add_scalar(k, v['value'], global_step=v['step'])

    # def step(self):
    #     self.global_step += 1
    #     for k, v in self.logger.items():
    #         self.writer.add_scalar(k, v['value'], global_step=v['step'])

def launch_tensorboard(tracking_address):
    # https://stackoverflow.com/a/55708102
    # tb will run in background but it will
    # be stopped once the main process is stopped.
    try:
        tb = program.TensorBoard()
        tb.configure(argv=[None, '--logdir', tracking_address, '--port', '8899'])
        url = tb.launch()
        if url.endswith("/"):
            url = url[:-1]

        return url
    except Exception:
        return None

def save_checkpoint(model, optimizer, mix_scaler, current_steps, current_epochs, args, info, filename):
    log_path = os.path.join(args['LOG'], filename)
    torch.save(
        {
            'weights': model.state_dict(),
            'optimizer': optimizer.state_dict(),
            'mix_scaler': mix_scaler.state_dict(),
            'current_steps': current_steps,
            'current_epochs': current_epochs,
            'args': args,
            'info': info
        },
        log_path
    )

def load_checkpoint(filename):
    '''
    Load the checkpoint by its absolute path

    :param filename:
    :return:
    '''
    # Print the previous ckpt information
    ckpt = torch.load(filename)
    print(f"Loaded checkpoint start from:\n{ckpt['info']}")

    # Initial model and load the trained weights
    ckpt_args = ckpt['args']

    if ckpt_args['TYPE'] == 'Encoder':
        model = Encoder(ckpt_args)

    elif ckpt_args['TYPE'] == 'CP2K' or ckpt_args['TYPE'] == 'CP2K_RNN' or ckpt_args['TYPE'] == 'CP2K_RNN_ENC':
        model = cp_2_k_mask(args=ckpt_args, out_channels=26)

    if ckpt_args['USE_COMPILE'] != 0:
        model = torch.compile(model)


    model.load_state_dict(ckpt['weights'])
    model.to(ckpt_args['DEVICE'])

    optimizer = optim.Adam(model.parameters(), lr=ckpt_args['LEARNING_RATE'], betas=[ckpt_args['BETA1'], ckpt_args['BETA1']], eps=ckpt_args['EPS'])
    optimizer.load_state_dict(ckpt['optimizer'])

    mix_scaler = torch.cuda.amp.GradScaler()
    mix_scaler.load_state_dict(ckpt['mix_scaler'])

    current_steps = ckpt['current_steps']
    current_epochs = ckpt['current_epochs']
    return model, optimizer, current_steps, current_epochs, mix_scaler, ckpt_args

if __name__ == "__main__":
    # log = TensorboardLogger()
    # torch.save(log, 'log.th')

    log = torch.load('log.th')